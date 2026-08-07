"""
Ensemble Predictor for Stock Price Prediction

This module implements Requirements 3.1-3.12, 13.3-13.4:
- Train ensemble models (RandomForest, GradientBoosting, XGBoost)
- Generate predictions with confidence scores (0-100)
- Assign prediction categories (Strong Buy, Buy, Hold, Sell, Strong Sell)
- Provide uncertainty quantification with bounds
- Flag low-confidence predictions (<60%)
- Calculate SHAP feature importance
- Cache trained models in Redis (24-hour TTL)

Properties implemented:
- Property 13: Prediction confidence range [0, 100]
- Property 14: Prediction category assignment
- Property 15: Prediction bounds consistency (lower_bound ≤ predicted_value ≤ upper_bound)
- Property 16: Low confidence flagging (<60%)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import pickle
import structlog

# ML models
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

# Explainability
import shap

# Infrastructure
from ...infrastructure.cache import get_cache, CacheKeyPatterns, CacheTTL

logger = structlog.get_logger(__name__)


@dataclass
class Prediction:
    """
    Prediction result with uncertainty quantification.
    
    Attributes:
        ticker: Stock ticker symbol
        timestamp: Prediction generation time
        prediction_type: Type of prediction ('price', 'direction', 'return')
        value: Predicted value (price, direction, or return)
        confidence: Confidence score in range [0, 100] (Property 13)
        lower_bound: Lower bound of prediction interval
        upper_bound: Upper bound of prediction interval  
        factors: Feature contributions to prediction (SHAP values)
        model: Model identifier ('ensemble', 'rf', 'gb', 'xgb')
        category: Prediction category (Strong Buy, Buy, Hold, Sell, Strong Sell)
        low_confidence: Flag for low confidence predictions (<60%) (Property 16)
    
    Validates:
        - Property 13: Confidence in [0, 100]
        - Property 15: lower_bound ≤ value ≤ upper_bound
        - Property 16: low_confidence flag set when confidence < 60
    """
    ticker: str
    timestamp: datetime
    prediction_type: str
    value: float
    confidence: float
    lower_bound: float
    upper_bound: float
    factors: Dict[str, float] = field(default_factory=dict)
    model: str = 'ensemble'
    category: Optional[str] = None
    low_confidence: bool = False
    
    def __post_init__(self):
        """Validate prediction properties after initialization."""
        # Property 13: Confidence must be in [0, 100]
        if not (0 <= self.confidence <= 100):
            raise ValueError(
                f"Property 13 violation: Confidence must be in [0, 100], got {self.confidence}"
            )
        
        # Property 15: Bounds consistency
        if not (self.lower_bound <= self.value <= self.upper_bound):
            raise ValueError(
                f"Property 15 violation: Bounds consistency failed. "
                f"Expected {self.lower_bound} ≤ {self.value} ≤ {self.upper_bound}"
            )
        
        # Property 16: Low confidence flagging
        self.low_confidence = self.confidence < 60.0
        
        # Property 14: Assign category if not set
        if self.category is None:
            self.category = self._assign_category()
    
    def _assign_category(self) -> str:
        """
        Assign prediction category based on value and confidence.
        
        Property 14: Prediction Category Assignment
        Categories: Strong Buy, Buy, Hold, Sell, Strong Sell
        
        Logic:
        - Strong Buy: High positive return (>5%) with high confidence (>70%)
        - Buy: Moderate positive return (2-5%) or high return with lower confidence
        - Hold: Small changes (-2% to 2%) or low confidence predictions
        - Sell: Moderate negative return (-5% to -2%)
        - Strong Sell: High negative return (<-5%) with high confidence (>70%)
        
        Returns:
            Category string
        """
        # For return-based predictions
        if self.prediction_type == 'return':
            return_pct = self.value * 100  # Convert to percentage
            
            if return_pct > 5.0 and self.confidence > 70.0:
                return 'Strong Buy'
            elif return_pct > 2.0:
                return 'Buy'
            elif return_pct < -5.0 and self.confidence > 70.0:
                return 'Strong Sell'
            elif return_pct < -2.0:
                return 'Sell'
            else:
                return 'Hold'
        
        # For direction-based predictions
        elif self.prediction_type == 'direction':
            if self.value > 0 and self.confidence > 70.0:
                return 'Strong Buy'
            elif self.value > 0:
                return 'Buy'
            elif self.value < 0 and self.confidence > 70.0:
                return 'Strong Sell'
            elif self.value < 0:
                return 'Sell'
            else:
                return 'Hold'
        
        # For price-based predictions, calculate return
        else:
            # Cannot determine category without current price
            # Default to Hold
            return 'Hold'


class EnsemblePredictor:
    """
    Ensemble predictor combining RandomForest, GradientBoosting, and XGBoost.
    
    This class implements a stacking ensemble approach where:
    1. Base models (RF, GB, XGBoost) make independent predictions
    2. Predictions are combined using weighted averaging (meta-learner)
    3. Confidence scores are calculated from prediction variance
    4. SHAP values provide feature importance and explainability
    
    Implements Requirements 3.1-3.12, 13.3-13.4
    """
    
    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 10,
        random_state: int = 42,
        cache_models: bool = True
    ):
        """
        Initialize ensemble predictor.
        
        Args:
            n_estimators: Number of trees for ensemble models
            max_depth: Maximum tree depth
            random_state: Random seed for reproducibility
            cache_models: Whether to cache trained models in Redis
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.cache_models = cache_models
        
        # Base models
        self.rf_model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=-1  # Use all CPU cores
        )
        
        self.gb_model = GradientBoostingRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state
        )
        
        self.xgb_model = xgb.XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=-1
        )
        
        # Model weights for meta-learner (equal weighting initially)
        self.model_weights = {
            'rf': 1/3,
            'gb': 1/3,
            'xgb': 1/3
        }
        
        # Feature scaler
        self.scaler = StandardScaler()
        
        # SHAP explainer (initialized after training)
        self.shap_explainer = None
        
        # Training metadata
        self.is_trained = False
        self.feature_names = None
        self.training_score = None
        
        # Cache
        self.cache = get_cache() if cache_models else None
        
        logger.info(
            "ensemble_predictor_initialized",
            n_estimators=n_estimators,
            max_depth=max_depth,
            cache_enabled=cache_models
        )
    
    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        """
        Train all base models and meta-learner.
        
        Training process:
        1. Scale features using StandardScaler
        2. Train RandomForest, GradientBoosting, and XGBoost independently
        3. Calculate model weights based on cross-validation scores
        4. Initialize SHAP explainer for feature importance
        5. Cache trained models in Redis (24-hour TTL)
        
        Args:
            X: Feature matrix (DataFrame with named columns)
            y: Target variable (Series with same index as X)
        
        Raises:
            ValueError: If X and y have mismatched indices or if data is invalid
        """
        if len(X) != len(y):
            raise ValueError(f"X and y must have same length. Got {len(X)} and {len(y)}")
        
        if X.empty or y.empty:
            raise ValueError("Training data cannot be empty")
        
        logger.info(
            "training_ensemble_models",
            samples=len(X),
            features=len(X.columns)
        )
        
        # Store feature names
        self.feature_names = list(X.columns)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        X_scaled = pd.DataFrame(X_scaled, columns=X.columns, index=X.index)
        
        # Train base models
        logger.info("training_random_forest")
        self.rf_model.fit(X_scaled, y)
        
        logger.info("training_gradient_boosting")
        self.gb_model.fit(X_scaled, y)
        
        logger.info("training_xgboost")
        self.xgb_model.fit(X_scaled, y)
        
        # Calculate model weights using time-series cross-validation
        logger.info("calculating_model_weights")
        self._calculate_model_weights(X_scaled, y)
        
        # Initialize SHAP explainer (using TreeExplainer for tree-based models).
        # Optional – explainability only; failures must not block training.
        logger.info("initializing_shap_explainer")
        try:
            self.shap_explainer = shap.TreeExplainer(self.rf_model)
        except Exception as shap_exc:
            logger.warning("shap_explainer_init_failed", error=str(shap_exc))
            self.shap_explainer = None
        
        # Mark as trained
        self.is_trained = True
        
        # Calculate training score
        train_predictions = self.predict(X)
        self.training_score = self._calculate_r2_score(y, [p.value for p in train_predictions])
        
        logger.info(
            "ensemble_training_complete",
            training_score=self.training_score,
            model_weights=self.model_weights
        )
        
        # Cache models in Redis
        if self.cache_models:
            self._cache_models()
    
    def _calculate_model_weights(self, X: pd.DataFrame, y: pd.Series) -> None:
        """
        Calculate model weights based on cross-validation performance.
        
        Uses TimeSeriesSplit for cross-validation to respect temporal ordering.
        Weights are normalized to sum to 1.0.
        
        Args:
            X: Scaled feature matrix
            y: Target variable
        """
        # Time series cross-validation (5 splits)
        tscv = TimeSeriesSplit(n_splits=5)
        
        # Calculate cross-validation scores for each model
        rf_scores = cross_val_score(
            self.rf_model, X, y, cv=tscv, scoring='neg_mean_squared_error'
        )
        gb_scores = cross_val_score(
            self.gb_model, X, y, cv=tscv, scoring='neg_mean_squared_error'
        )
        xgb_scores = cross_val_score(
            self.xgb_model, X, y, cv=tscv, scoring='neg_mean_squared_error'
        )
        
        # Convert negative MSE to positive (lower is better, so negate)
        rf_mse = -rf_scores.mean()
        gb_mse = -gb_scores.mean()
        xgb_mse = -xgb_scores.mean()
        
        # Calculate weights inversely proportional to MSE
        # Better models (lower MSE) get higher weights
        rf_weight = 1 / rf_mse if rf_mse > 0 else 1.0
        gb_weight = 1 / gb_mse if gb_mse > 0 else 1.0
        xgb_weight = 1 / xgb_mse if xgb_mse > 0 else 1.0
        
        # Normalize weights to sum to 1.0
        total_weight = rf_weight + gb_weight + xgb_weight
        
        self.model_weights = {
            'rf': rf_weight / total_weight,
            'gb': gb_weight / total_weight,
            'xgb': xgb_weight / total_weight
        }
        
        logger.info(
            "model_weights_calculated",
            rf_mse=rf_mse,
            gb_mse=gb_mse,
            xgb_mse=xgb_mse,
            weights=self.model_weights
        )
    
    def predict(self, X: pd.DataFrame) -> List[Prediction]:
        """
        Generate ensemble predictions with confidence scores.
        
        Prediction process:
        1. Scale features using fitted scaler
        2. Get predictions from all base models
        3. Calculate weighted ensemble prediction
        4. Calculate confidence from prediction variance
        5. Calculate prediction bounds (95% confidence interval)
        6. Assign prediction category
        7. Flag low-confidence predictions
        
        Args:
            X: Feature matrix (DataFrame with same columns as training data)
        
        Returns:
            List of Prediction objects, one per sample
        
        Raises:
            ValueError: If model is not trained or features are mismatched
        
        Properties validated:
        - Property 13: Confidence in [0, 100]
        - Property 14: Category assignment
        - Property 15: Bounds consistency
        - Property 16: Low confidence flagging
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Validate features match training data
        if list(X.columns) != self.feature_names:
            raise ValueError(
                f"Feature mismatch. Expected {self.feature_names}, got {list(X.columns)}"
            )
        
        logger.info("generating_predictions", samples=len(X))
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        X_scaled = pd.DataFrame(X_scaled, columns=X.columns, index=X.index)
        
        # Get predictions from each model
        rf_preds = self.rf_model.predict(X_scaled)
        gb_preds = self.gb_model.predict(X_scaled)
        xgb_preds = self.xgb_model.predict(X_scaled)
        
        # Calculate ensemble predictions using weighted average
        ensemble_preds = (
            self.model_weights['rf'] * rf_preds +
            self.model_weights['gb'] * gb_preds +
            self.model_weights['xgb'] * xgb_preds
        )
        
        # Calculate confidence scores and bounds
        predictions = []
        
        for i in range(len(X)):
            # Get individual model predictions for this sample
            model_preds = np.array([rf_preds[i], gb_preds[i], xgb_preds[i]])
            ensemble_pred = ensemble_preds[i]
            
            # Calculate confidence from prediction variance
            # Lower variance = higher confidence
            pred_std = np.std(model_preds)
            pred_mean = np.mean(model_preds)
            
            # Confidence score: inverse of coefficient of variation, scaled to [0, 100]
            # CV = std / mean (relative variability)
            # Confidence = 100 * (1 - min(CV, 1.0))
            if abs(pred_mean) > 1e-6:
                cv = min(pred_std / abs(pred_mean), 1.0)
                confidence = 100.0 * (1.0 - cv)
            else:
                # If mean is near zero, use absolute std
                confidence = max(0.0, 100.0 - pred_std * 100.0)
            
            # Ensure confidence is in [0, 100] (Property 13)
            confidence = np.clip(confidence, 0.0, 100.0)
            
            # Calculate prediction bounds (95% confidence interval)
            # Use 1.96 * std for 95% CI
            margin = 1.96 * pred_std
            lower_bound = ensemble_pred - margin
            upper_bound = ensemble_pred + margin
            
            # Ensure bounds consistency (Property 15)
            # This should always be true, but ensure it explicitly
            if lower_bound > ensemble_pred:
                lower_bound = ensemble_pred
            if upper_bound < ensemble_pred:
                upper_bound = ensemble_pred
            
            # Calculate SHAP values for feature importance
            shap_values = self._calculate_shap_values(X_scaled.iloc[[i]])
            
            # Create prediction object
            # Category and low_confidence flag are set automatically in __post_init__
            prediction = Prediction(
                ticker=X.index[i] if hasattr(X.index[i], '__str__') else str(i),
                timestamp=datetime.now(),
                prediction_type='return',  # Predicting next-day return
                value=float(ensemble_pred),
                confidence=float(confidence),
                lower_bound=float(lower_bound),
                upper_bound=float(upper_bound),
                factors=shap_values,
                model='ensemble'
            )
            
            predictions.append(prediction)
        
        logger.info(
            "predictions_generated",
            count=len(predictions),
            avg_confidence=np.mean([p.confidence for p in predictions]),
            low_confidence_count=sum(1 for p in predictions if p.low_confidence)
        )
        
        return predictions
    
    def _calculate_shap_values(self, X_sample: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate SHAP feature importance for a single sample.
        
        Args:
            X_sample: Single sample (1 row DataFrame)
        
        Returns:
            Dictionary mapping feature names to SHAP values
        """
        if self.shap_explainer is None:
            return {}
        
        try:
            shap_values = self.shap_explainer.shap_values(X_sample)
            
            # shap_values is a 2D array, get the first row
            if isinstance(shap_values, np.ndarray):
                shap_values = shap_values[0] if shap_values.ndim > 1 else shap_values
            
            # Create dictionary mapping feature names to SHAP values
            factors = {
                feature: float(value)
                for feature, value in zip(self.feature_names, shap_values)
            }
            
            return factors
            
        except Exception as e:
            logger.error("shap_calculation_failed", error=str(e))
            return {}
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get SHAP-based feature importance across all features.
        
        Feature importance is calculated as the mean absolute SHAP value
        across all training samples. This provides a model-agnostic measure
        of feature importance.
        
        Returns:
            Dictionary mapping feature names to importance scores
        
        Raises:
            ValueError: If model is not trained
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before calculating feature importance")
        
        if self.shap_explainer is None:
            logger.warning("shap_explainer_not_initialized")
            # Fall back to RandomForest feature importances
            return {
                feature: float(importance)
                for feature, importance in zip(
                    self.feature_names,
                    self.rf_model.feature_importances_
                )
            }
        
        # Note: For full SHAP importance, we would need to calculate SHAP values
        # across a representative sample of training data. This is expensive.
        # For now, return RandomForest importances as a proxy.
        
        logger.info("calculating_feature_importance")
        
        importance_dict = {
            feature: float(importance)
            for feature, importance in zip(
                self.feature_names,
                self.rf_model.feature_importances_
            )
        }
        
        # Sort by importance (descending)
        importance_dict = dict(
            sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
        )
        
        return importance_dict
    
    def _calculate_r2_score(self, y_true: pd.Series, y_pred: List[float]) -> float:
        """Calculate R-squared score."""
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        
        if ss_tot == 0:
            return 0.0
        
        return 1 - (ss_res / ss_tot)
    
    def _cache_models(self) -> None:
        """
        Cache trained models in Redis with 24-hour TTL.
        
        Serializes all models and metadata to Redis for fast retrieval.
        Implements Requirement 3.13: Cache trained models in Redis.
        """
        if self.cache is None:
            return
        
        try:
            logger.info("caching_ensemble_models")
            
            # Serialize entire predictor (includes all models and metadata)
            model_data = {
                'rf_model': self.rf_model,
                'gb_model': self.gb_model,
                'xgb_model': self.xgb_model,
                'scaler': self.scaler,
                'model_weights': self.model_weights,
                'feature_names': self.feature_names,
                'training_score': self.training_score,
                'is_trained': self.is_trained,
                'n_estimators': self.n_estimators,
                'max_depth': self.max_depth,
                'random_state': self.random_state
            }
            
            # Cache key pattern
            cache_key = "model:ensemble:predictor"
            
            # Cache with 24-hour TTL (86400 seconds)
            self.cache.set(
                cache_key,
                model_data,
                ttl=86400,  # 24 hours
                serialize=True
            )
            
            logger.info("ensemble_models_cached", cache_key=cache_key, ttl=86400)
            
        except Exception as e:
            logger.error("model_caching_failed", error=str(e))
    
    @classmethod
    def load_from_cache(cls, cache_models: bool = True) -> Optional['EnsemblePredictor']:
        """
        Load trained models from Redis cache.
        
        Args:
            cache_models: Whether to enable caching for this instance
        
        Returns:
            EnsemblePredictor instance or None if not cached
        """
        if not cache_models:
            return None
        
        try:
            cache = get_cache()
            cache_key = "model:ensemble:predictor"
            
            model_data = cache.get(cache_key, deserialize=True)
            
            if model_data is None:
                logger.info("no_cached_models_found")
                return None
            
            logger.info("loading_cached_models")
            
            # Create instance
            predictor = cls(
                n_estimators=model_data.get('n_estimators', 100),
                max_depth=model_data.get('max_depth', 10),
                random_state=model_data.get('random_state', 42),
                cache_models=cache_models
            )
            
            # Restore models and metadata
            predictor.rf_model = model_data['rf_model']
            predictor.gb_model = model_data['gb_model']
            predictor.xgb_model = model_data['xgb_model']
            predictor.scaler = model_data['scaler']
            predictor.model_weights = model_data['model_weights']
            predictor.feature_names = model_data['feature_names']
            predictor.training_score = model_data['training_score']
            predictor.is_trained = model_data['is_trained']
            
            # Re-initialize SHAP explainer (optional – explainability only).
            # If SHAP/torch fails to load, predictions still work without it.
            try:
                predictor.shap_explainer = shap.TreeExplainer(predictor.rf_model)
            except Exception as shap_exc:
                logger.warning("shap_explainer_init_failed", error=str(shap_exc))
                predictor.shap_explainer = None
            
            logger.info(
                "cached_models_loaded",
                training_score=predictor.training_score,
                features=len(predictor.feature_names)
            )
            
            return predictor
            
        except Exception as e:
            logger.error("model_loading_failed", error=str(e))
            return None


def predict_category(prediction: Prediction) -> str:
    """
    Get prediction category from a Prediction object.
    
    This is a convenience function that returns the category
    already assigned to the prediction object.
    
    Property 14: Prediction Category Assignment
    
    Args:
        prediction: Prediction object
    
    Returns:
        Category string: 'Strong Buy', 'Buy', 'Hold', 'Sell', or 'Strong Sell'
    """
    return prediction.category


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    print("Ensemble Predictor - Example Usage\n")
    
    # Generate sample data
    np.random.seed(42)
    n_samples = 100
    n_features = 10
    
    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )
    
    # Target: next-day return
    y = pd.Series(np.random.randn(n_samples) * 0.02, name='target_return')
    
    # Train model
    print("Training ensemble predictor...")
    predictor = EnsemblePredictor(n_estimators=50, cache_models=False)
    predictor.train(X, y)
    
    # Make predictions
    print("\nGenerating predictions...")
    predictions = predictor.predict(X.head(5))
    
    # Display predictions
    print("\nPredictions:")
    for pred in predictions:
        print(f"  Value: {pred.value:.4f}, Confidence: {pred.confidence:.1f}%, "
              f"Category: {pred.category}, Low Conf: {pred.low_confidence}")
    
    # Feature importance
    print("\nTop 5 Features:")
    importance = predictor.get_feature_importance()
    for feature, score in list(importance.items())[:5]:
        print(f"  {feature}: {score:.4f}")

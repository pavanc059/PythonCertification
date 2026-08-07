"""
Anomaly Detection for Market Data

This module implements anomaly detection using Isolation Forests and Autoencoders
to identify unusual market patterns that may signal trading opportunities or risks.

Requirements: 13.6
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import logging

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """
    Data class representing an anomaly detection result.
    
    Attributes:
        ticker: Stock ticker symbol
        timestamp: Detection timestamp
        is_anomaly: Whether the data point is an anomaly
        anomaly_score: Anomaly score (higher = more anomalous)
        confidence: Confidence score (0-100%)
        contributing_features: Features that contributed most to anomaly
        reconstruction_error: Reconstruction error (for autoencoder)
        method: Detection method used ('isolation_forest', 'autoencoder', 'ensemble')
        metadata: Additional metadata
    """
    ticker: str
    timestamp: datetime
    is_anomaly: bool
    anomaly_score: float
    confidence: float
    contributing_features: Dict[str, float] = field(default_factory=dict)
    reconstruction_error: Optional[float] = None
    method: str = "unknown"
    metadata: Optional[Dict] = None
    
    def __post_init__(self):
        """Validate anomaly result after initialization"""
        if not 0 <= self.confidence <= 100:
            raise ValueError(f"Confidence must be between 0 and 100, got {self.confidence}")


class AutoencoderModel(nn.Module):
    """
    Autoencoder Neural Network for Anomaly Detection.
    
    Architecture:
        Input → Encoder → Bottleneck → Decoder → Output
        
    The autoencoder learns to compress and reconstruct normal market data.
    Anomalies have high reconstruction error because they differ from normal patterns.
    """
    
    def __init__(
        self,
        input_size: int,
        hidden_sizes: List[int] = None,
        bottleneck_size: int = 8,
        dropout: float = 0.2
    ):
        """
        Initialize Autoencoder model.
        
        Args:
            input_size: Number of input features
            hidden_sizes: List of hidden layer sizes (default [64, 32, 16])
            bottleneck_size: Size of the bottleneck layer (default 8)
            dropout: Dropout probability for regularization (default 0.2)
        """
        super(AutoencoderModel, self).__init__()
        
        if hidden_sizes is None:
            hidden_sizes = [64, 32, 16]
        
        self.input_size = input_size
        self.hidden_sizes = hidden_sizes
        self.bottleneck_size = bottleneck_size
        self.dropout = dropout
        
        # Build encoder
        encoder_layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            encoder_layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_size = hidden_size
        
        # Bottleneck layer
        encoder_layers.append(nn.Linear(prev_size, bottleneck_size))
        
        self.encoder = nn.Sequential(*encoder_layers)
        
        # Build decoder (mirror of encoder)
        decoder_layers = []
        prev_size = bottleneck_size
        
        for hidden_size in reversed(hidden_sizes):
            decoder_layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_size = hidden_size
        
        # Output layer
        decoder_layers.append(nn.Linear(prev_size, input_size))
        
        self.decoder = nn.Sequential(*decoder_layers)
        
        logger.info(
            f"Initialized Autoencoder: input_size={input_size}, "
            f"hidden_sizes={hidden_sizes}, bottleneck_size={bottleneck_size}"
        )
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through autoencoder.
        
        Args:
            x: Input tensor of shape (batch_size, input_size)
            
        Returns:
            Tuple of (reconstructed output, encoded representation)
        """
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded, encoded


class IsolationForestDetector:
    """
    Isolation Forest-based anomaly detector for market data.
    
    Isolation Forest works by:
    1. Randomly selecting features and split values
    2. Building isolation trees that partition the data
    3. Anomalies are isolated faster (fewer splits needed)
    4. Anomaly score based on average path length
    
    Advantages:
    - Fast and scalable
    - Handles high-dimensional data well
    - No assumptions about data distribution
    - Works well for global anomalies
    
    Requirements: 13.6
    """
    
    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        max_samples: Union[int, str] = 'auto',
        random_state: int = 42
    ):
        """
        Initialize Isolation Forest detector.
        
        Args:
            contamination: Expected proportion of anomalies (default 0.1 = 10%)
            n_estimators: Number of isolation trees (default 100)
            max_samples: Number of samples to draw for each tree (default 'auto')
            random_state: Random seed for reproducibility (default 42)
        """
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.random_state = random_state
        
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            max_samples=max_samples,
            random_state=random_state,
            n_jobs=-1  # Use all CPU cores
        )
        
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names = None
        
        logger.info(
            f"Initialized IsolationForestDetector: contamination={contamination}, "
            f"n_estimators={n_estimators}"
        )
    
    def train(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        feature_names: Optional[List[str]] = None
    ) -> None:
        """
        Train the Isolation Forest on normal market data.
        
        Args:
            X: Training data, shape (num_samples, num_features)
            feature_names: Optional list of feature names for interpretation
        """
        if isinstance(X, pd.DataFrame):
            self.feature_names = list(X.columns)
            X = X.values
        elif feature_names is not None:
            self.feature_names = feature_names
        else:
            self.feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        
        logger.info(f"Training Isolation Forest on {len(X)} samples with {X.shape[1]} features")
        
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Isolation Forest
        self.model.fit(X_scaled)
        
        self.is_fitted = True
        logger.info("Isolation Forest training completed")
    
    def detect(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        ticker: str = "UNKNOWN",
        return_top_features: int = 5
    ) -> List[AnomalyResult]:
        """
        Detect anomalies in market data.
        
        Args:
            X: Data to check for anomalies, shape (num_samples, num_features)
            ticker: Stock ticker symbol
            return_top_features: Number of top contributing features to return
            
        Returns:
            List of AnomalyResult objects for each sample
        """
        if not self.is_fitted:
            raise ValueError("Detector must be trained before detecting anomalies")
        
        if isinstance(X, pd.DataFrame):
            X = X.values
        
        # Normalize features
        X_scaled = self.scaler.transform(X)
        
        # Predict anomalies (-1 for anomalies, 1 for normal)
        predictions = self.model.predict(X_scaled)
        
        # Get anomaly scores (lower = more anomalous)
        scores = self.model.score_samples(X_scaled)
        
        # Convert scores to [0, 1] range (higher = more anomalous)
        # Isolation Forest scores are negative, more negative = more anomalous
        min_score = scores.min()
        max_score = scores.max()
        normalized_scores = (max_score - scores) / (max_score - min_score + 1e-8)
        
        # Create results
        results = []
        for i in range(len(X)):
            is_anomaly = predictions[i] == -1
            anomaly_score = float(normalized_scores[i])
            
            # Calculate confidence based on score magnitude
            confidence = float(anomaly_score * 100)
            
            # Identify contributing features
            # Features with extreme values (far from mean) contribute more
            feature_deviations = np.abs(X_scaled[i] - X_scaled.mean(axis=0))
            top_indices = np.argsort(feature_deviations)[-return_top_features:][::-1]
            
            contributing_features = {
                self.feature_names[idx]: float(feature_deviations[idx])
                for idx in top_indices
            }
            
            result = AnomalyResult(
                ticker=ticker,
                timestamp=datetime.now(),
                is_anomaly=is_anomaly,
                anomaly_score=anomaly_score,
                confidence=confidence,
                contributing_features=contributing_features,
                method="isolation_forest",
                metadata={
                    'raw_score': float(scores[i]),
                    'prediction': int(predictions[i])
                }
            )
            
            results.append(result)
        
        logger.info(
            f"Detected {sum(r.is_anomaly for r in results)} anomalies out of {len(results)} samples"
        )
        
        return results


class AutoencoderDetector:
    """
    Autoencoder-based anomaly detector for market data.
    
    Autoencoder learns to compress and reconstruct normal market patterns.
    Anomalies have high reconstruction error because they differ from learned patterns.
    
    Advantages:
    - Captures complex non-linear patterns
    - Good for contextual anomalies
    - Learns feature interactions
    - Can provide reconstruction for interpretation
    
    Requirements: 13.6
    """
    
    def __init__(
        self,
        input_size: int,
        hidden_sizes: List[int] = None,
        bottleneck_size: int = 8,
        dropout: float = 0.2,
        learning_rate: float = 0.001,
        device: Optional[str] = None
    ):
        """
        Initialize Autoencoder detector.
        
        Args:
            input_size: Number of input features
            hidden_sizes: List of hidden layer sizes (default [64, 32, 16])
            bottleneck_size: Size of bottleneck layer (default 8)
            dropout: Dropout probability (default 0.2)
            learning_rate: Learning rate for optimizer (default 0.001)
            device: Device for computation ('cpu', 'cuda', or None for auto-detect)
        """
        # Detect device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        logger.info(f"Using device: {self.device}")
        
        # Initialize model
        self.model = AutoencoderModel(
            input_size=input_size,
            hidden_sizes=hidden_sizes,
            bottleneck_size=bottleneck_size,
            dropout=dropout
        ).to(self.device)
        
        # Optimizer and loss
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()
        
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names = None
        self.threshold = None
        
        # Hyperparameters
        self.input_size = input_size
        self.learning_rate = learning_rate
    
    def train(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        epochs: int = 100,
        batch_size: int = 32,
        threshold_percentile: float = 95.0,
        feature_names: Optional[List[str]] = None,
        verbose: bool = True
    ) -> Dict[str, List[float]]:
        """
        Train the autoencoder on normal market data.
        
        Args:
            X: Training data (normal data only), shape (num_samples, num_features)
            epochs: Number of training epochs (default 100)
            batch_size: Batch size for training (default 32)
            threshold_percentile: Percentile for anomaly threshold (default 95.0)
            feature_names: Optional list of feature names
            verbose: Print training progress (default True)
            
        Returns:
            Dictionary with training history
        """
        if isinstance(X, pd.DataFrame):
            self.feature_names = list(X.columns)
            X = X.values
        elif feature_names is not None:
            self.feature_names = feature_names
        else:
            self.feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        
        logger.info(f"Training Autoencoder on {len(X)} samples with {X.shape[1]} features")
        logger.info(f"Epochs: {epochs}, Batch size: {batch_size}")
        
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        X_tensor = torch.FloatTensor(X_scaled).to(self.device)
        
        # Training loop
        history = {'loss': []}
        
        for epoch in range(epochs):
            self.model.train()
            epoch_losses = []
            
            # Mini-batch training
            for i in range(0, len(X_tensor), batch_size):
                batch_X = X_tensor[i:i+batch_size]
                
                # Forward pass
                self.optimizer.zero_grad()
                reconstructed, _ = self.model(batch_X)
                loss = self.criterion(reconstructed, batch_X)
                
                # Backward pass
                loss.backward()
                self.optimizer.step()
                
                epoch_losses.append(loss.item())
            
            avg_loss = np.mean(epoch_losses)
            history['loss'].append(avg_loss)
            
            if verbose and (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.6f}")
        
        # Calculate anomaly threshold based on reconstruction errors
        self.model.eval()
        with torch.no_grad():
            reconstructed, _ = self.model(X_tensor)
            reconstruction_errors = torch.mean((X_tensor - reconstructed) ** 2, dim=1)
            self.threshold = float(np.percentile(
                reconstruction_errors.cpu().numpy(),
                threshold_percentile
            ))
        
        self.is_fitted = True
        logger.info(f"Training completed. Anomaly threshold set to: {self.threshold:.6f}")
        
        return history
    
    def detect(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        ticker: str = "UNKNOWN",
        return_top_features: int = 5
    ) -> List[AnomalyResult]:
        """
        Detect anomalies using reconstruction error.
        
        Args:
            X: Data to check for anomalies, shape (num_samples, num_features)
            ticker: Stock ticker symbol
            return_top_features: Number of top contributing features to return
            
        Returns:
            List of AnomalyResult objects for each sample
        """
        if not self.is_fitted:
            raise ValueError("Detector must be trained before detecting anomalies")
        
        if isinstance(X, pd.DataFrame):
            X = X.values
        
        # Normalize features
        X_scaled = self.scaler.transform(X)
        X_tensor = torch.FloatTensor(X_scaled).to(self.device)
        
        # Get reconstructions
        self.model.eval()
        with torch.no_grad():
            reconstructed, _ = self.model(X_tensor)
            
            # Calculate reconstruction error per sample
            reconstruction_errors = torch.mean(
                (X_tensor - reconstructed) ** 2,
                dim=1
            ).cpu().numpy()
            
            # Calculate per-feature reconstruction errors
            feature_errors = ((X_tensor - reconstructed) ** 2).cpu().numpy()
        
        # Normalize scores to [0, 1] range
        max_error = reconstruction_errors.max()
        normalized_scores = reconstruction_errors / (max_error + 1e-8)
        
        # Create results
        results = []
        for i in range(len(X)):
            reconstruction_error = float(reconstruction_errors[i])
            is_anomaly = reconstruction_error > self.threshold
            anomaly_score = float(normalized_scores[i])
            
            # Calculate confidence
            if is_anomaly:
                # How much above threshold
                confidence = min(100, (reconstruction_error / self.threshold - 1) * 100 + 50)
            else:
                # How much below threshold
                confidence = max(0, (1 - reconstruction_error / self.threshold) * 100)
            
            # Identify contributing features (highest reconstruction errors)
            top_indices = np.argsort(feature_errors[i])[-return_top_features:][::-1]
            
            contributing_features = {
                self.feature_names[idx]: float(feature_errors[i, idx])
                for idx in top_indices
            }
            
            result = AnomalyResult(
                ticker=ticker,
                timestamp=datetime.now(),
                is_anomaly=is_anomaly,
                anomaly_score=anomaly_score,
                confidence=float(confidence),
                contributing_features=contributing_features,
                reconstruction_error=reconstruction_error,
                method="autoencoder",
                metadata={
                    'threshold': self.threshold,
                    'raw_error': reconstruction_error
                }
            )
            
            results.append(result)
        
        logger.info(
            f"Detected {sum(r.is_anomaly for r in results)} anomalies out of {len(results)} samples"
        )
        
        return results


class AnomalyDetector:
    """
    Ensemble anomaly detector combining Isolation Forest and Autoencoder.
    
    This class combines both detection methods:
    - Isolation Forest: Fast, good for global anomalies
    - Autoencoder: Captures complex patterns, good for contextual anomalies
    
    The ensemble approach provides more robust detection by combining strengths
    of both methods.
    
    Requirements: 13.6
    
    Example:
        >>> from stockiq.models.features import create_feature_matrix
        >>> 
        >>> # Create features for normal market data
        >>> normal_data = create_feature_matrix('AAPL', lookback_days=365)
        >>> X_normal = normal_data.drop(['target_return', 'target_direction'], axis=1)
        >>> 
        >>> # Train detector
        >>> detector = AnomalyDetector(input_size=X_normal.shape[1])
        >>> detector.train(X_normal)
        >>> 
        >>> # Detect anomalies in new data
        >>> new_data = create_feature_matrix('AAPL', lookback_days=30)
        >>> X_new = new_data.drop(['target_return', 'target_direction'], axis=1)
        >>> results = detector.detect(X_new, ticker='AAPL')
        >>> 
        >>> # Print anomalies
        >>> for result in results:
        ...     if result.is_anomaly:
        ...         print(f"Anomaly detected: {result.ticker} - Score: {result.anomaly_score:.3f}")
        ...         print(f"Contributing features: {result.contributing_features}")
    """
    
    def __init__(
        self,
        input_size: int,
        use_isolation_forest: bool = True,
        use_autoencoder: bool = True,
        ensemble_method: str = "vote",
        **kwargs
    ):
        """
        Initialize ensemble anomaly detector.
        
        Args:
            input_size: Number of input features
            use_isolation_forest: Use Isolation Forest detector (default True)
            use_autoencoder: Use Autoencoder detector (default True)
            ensemble_method: How to combine results ('vote', 'average', 'max')
            **kwargs: Additional arguments passed to individual detectors
        """
        if not use_isolation_forest and not use_autoencoder:
            raise ValueError("At least one detection method must be enabled")
        
        self.input_size = input_size
        self.use_isolation_forest = use_isolation_forest
        self.use_autoencoder = use_autoencoder
        self.ensemble_method = ensemble_method
        
        # Initialize detectors
        self.isolation_forest = None
        self.autoencoder = None
        
        if use_isolation_forest:
            if_kwargs = {k: v for k, v in kwargs.items() if k in ['contamination', 'n_estimators', 'max_samples', 'random_state']}
            self.isolation_forest = IsolationForestDetector(**if_kwargs)
        
        if use_autoencoder:
            ae_kwargs = {k: v for k, v in kwargs.items() if k in ['hidden_sizes', 'bottleneck_size', 'dropout', 'learning_rate', 'device']}
            self.autoencoder = AutoencoderDetector(input_size=input_size, **ae_kwargs)
        
        self.is_fitted = False
        
        logger.info(
            f"Initialized AnomalyDetector: isolation_forest={use_isolation_forest}, "
            f"autoencoder={use_autoencoder}, ensemble_method={ensemble_method}"
        )
    
    def train(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        epochs: int = 100,
        batch_size: int = 32,
        feature_names: Optional[List[str]] = None,
        verbose: bool = True
    ) -> Dict[str, any]:
        """
        Train all enabled detectors.
        
        Args:
            X: Training data (normal data only), shape (num_samples, num_features)
            epochs: Number of epochs for autoencoder (default 100)
            batch_size: Batch size for autoencoder (default 32)
            feature_names: Optional list of feature names
            verbose: Print training progress (default True)
            
        Returns:
            Dictionary with training results for each detector
        """
        logger.info(f"Training anomaly detector ensemble on {len(X)} samples")
        
        results = {}
        
        # Train Isolation Forest
        if self.isolation_forest is not None:
            logger.info("Training Isolation Forest...")
            self.isolation_forest.train(X, feature_names=feature_names)
            results['isolation_forest'] = {'trained': True}
        
        # Train Autoencoder
        if self.autoencoder is not None:
            logger.info("Training Autoencoder...")
            history = self.autoencoder.train(
                X, epochs=epochs, batch_size=batch_size,
                feature_names=feature_names, verbose=verbose
            )
            results['autoencoder'] = {'trained': True, 'history': history}
        
        self.is_fitted = True
        logger.info("Ensemble training completed")
        
        return results
    
    def detect(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        ticker: str = "UNKNOWN",
        return_top_features: int = 5
    ) -> List[AnomalyResult]:
        """
        Detect anomalies using ensemble of methods.
        
        Args:
            X: Data to check for anomalies, shape (num_samples, num_features)
            ticker: Stock ticker symbol
            return_top_features: Number of top contributing features to return
            
        Returns:
            List of AnomalyResult objects combining both methods
        """
        if not self.is_fitted:
            raise ValueError("Detector must be trained before detecting anomalies")
        
        # Get results from individual detectors
        if_results = None
        ae_results = None
        
        if self.isolation_forest is not None:
            if_results = self.isolation_forest.detect(
                X, ticker=ticker, return_top_features=return_top_features
            )
        
        if self.autoencoder is not None:
            ae_results = self.autoencoder.detect(
                X, ticker=ticker, return_top_features=return_top_features
            )
        
        # Combine results based on ensemble method
        if self.use_isolation_forest and self.use_autoencoder:
            results = self._combine_results(
                if_results, ae_results, ticker, return_top_features
            )
        elif self.use_isolation_forest:
            results = if_results
        else:  # use_autoencoder only
            results = ae_results
        
        return results
    
    def _combine_results(
        self,
        if_results: List[AnomalyResult],
        ae_results: List[AnomalyResult],
        ticker: str,
        return_top_features: int
    ) -> List[AnomalyResult]:
        """
        Combine results from Isolation Forest and Autoencoder.
        
        Args:
            if_results: Results from Isolation Forest
            ae_results: Results from Autoencoder
            ticker: Stock ticker symbol
            return_top_features: Number of top features to return
            
        Returns:
            Combined list of AnomalyResult objects
        """
        combined_results = []
        
        for i in range(len(if_results)):
            if_res = if_results[i]
            ae_res = ae_results[i]
            
            # Combine based on ensemble method
            if self.ensemble_method == "vote":
                # Anomaly if both methods agree
                is_anomaly = if_res.is_anomaly and ae_res.is_anomaly
                confidence = (if_res.confidence + ae_res.confidence) / 2
                
            elif self.ensemble_method == "average":
                # Average the anomaly scores
                anomaly_score = (if_res.anomaly_score + ae_res.anomaly_score) / 2
                confidence = (if_res.confidence + ae_res.confidence) / 2
                # Anomaly if average score is high
                is_anomaly = anomaly_score > 0.5
                
            elif self.ensemble_method == "max":
                # Anomaly if either method detects it
                is_anomaly = if_res.is_anomaly or ae_res.is_anomaly
                anomaly_score = max(if_res.anomaly_score, ae_res.anomaly_score)
                confidence = max(if_res.confidence, ae_res.confidence)
            
            else:
                raise ValueError(f"Unknown ensemble method: {self.ensemble_method}")
            
            # Combine contributing features from both methods
            combined_features = {}
            all_features = set(if_res.contributing_features.keys()) | set(ae_res.contributing_features.keys())
            
            for feature in all_features:
                if_score = if_res.contributing_features.get(feature, 0)
                ae_score = ae_res.contributing_features.get(feature, 0)
                combined_features[feature] = (if_score + ae_score) / 2
            
            # Keep only top N features
            sorted_features = sorted(
                combined_features.items(),
                key=lambda x: x[1],
                reverse=True
            )[:return_top_features]
            top_features = dict(sorted_features)
            
            # Create combined result
            result = AnomalyResult(
                ticker=ticker,
                timestamp=datetime.now(),
                is_anomaly=is_anomaly,
                anomaly_score=anomaly_score if self.ensemble_method != "vote" else (if_res.anomaly_score + ae_res.anomaly_score) / 2,
                confidence=float(confidence),
                contributing_features=top_features,
                reconstruction_error=ae_res.reconstruction_error,
                method="ensemble",
                metadata={
                    'isolation_forest': {
                        'is_anomaly': if_res.is_anomaly,
                        'score': if_res.anomaly_score,
                        'confidence': if_res.confidence
                    },
                    'autoencoder': {
                        'is_anomaly': ae_res.is_anomaly,
                        'score': ae_res.anomaly_score,
                        'confidence': ae_res.confidence,
                        'reconstruction_error': ae_res.reconstruction_error
                    },
                    'ensemble_method': self.ensemble_method
                }
            )
            
            combined_results.append(result)
        
        logger.info(
            f"Ensemble detected {sum(r.is_anomaly for r in combined_results)} anomalies "
            f"out of {len(combined_results)} samples"
        )
        
        return combined_results


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    print("\nAnomaly Detection - Example Usage\n")
    print("=" * 60)
    
    # Create synthetic market data for testing
    print("\n1. Creating synthetic market data...")
    np.random.seed(42)
    torch.manual_seed(42)
    
    num_samples = 1000
    num_features = 20
    
    # Generate normal data (from standard normal distribution)
    X_normal = np.random.randn(num_samples, num_features).astype(np.float32)
    
    # Add some anomalies (extreme values)
    num_anomalies = 50
    anomaly_indices = np.random.choice(num_samples, num_anomalies, replace=False)
    X_normal[anomaly_indices] = np.random.randn(num_anomalies, num_features) * 5  # 5x larger variance
    
    print(f"Data shape: {X_normal.shape}")
    print(f"True anomalies: {num_anomalies} ({num_anomalies/num_samples*100:.1f}%)")
    
    # Split into train (normal data only) and test
    # For training, use only data points that are not anomalies
    mask_normal = np.ones(num_samples, dtype=bool)
    mask_normal[anomaly_indices] = False
    
    X_train = X_normal[mask_normal]
    X_test = X_normal  # Test on all data including anomalies
    
    print(f"Train: {X_train.shape[0]} samples (normal only)")
    print(f"Test: {X_test.shape[0]} samples (with anomalies)")
    
    # Test Isolation Forest
    print("\n2. Testing Isolation Forest Detector...")
    if_detector = IsolationForestDetector(contamination=0.05, n_estimators=100)
    if_detector.train(X_train)
    
    if_results = if_detector.detect(X_test[:100], ticker="TEST")  # Test on first 100 samples
    if_detected = sum(r.is_anomaly for r in if_results)
    print(f"Isolation Forest detected {if_detected} anomalies in 100 samples")
    
    # Test Autoencoder
    print("\n3. Testing Autoencoder Detector...")
    ae_detector = AutoencoderDetector(
        input_size=num_features,
        hidden_sizes=[32, 16, 8],
        bottleneck_size=4,
        dropout=0.1,
        learning_rate=0.001
    )
    
    ae_detector.train(X_train, epochs=50, batch_size=64, verbose=True)
    
    ae_results = ae_detector.detect(X_test[:100], ticker="TEST")
    ae_detected = sum(r.is_anomaly for r in ae_results)
    print(f"Autoencoder detected {ae_detected} anomalies in 100 samples")
    
    # Test Ensemble Detector
    print("\n4. Testing Ensemble Detector...")
    ensemble_detector = AnomalyDetector(
        input_size=num_features,
        use_isolation_forest=True,
        use_autoencoder=True,
        ensemble_method="vote",
        contamination=0.05,
        n_estimators=100,
        hidden_sizes=[32, 16, 8],
        bottleneck_size=4
    )
    
    ensemble_detector.train(X_train, epochs=30, batch_size=64, verbose=False)
    
    ensemble_results = ensemble_detector.detect(X_test[:100], ticker="TEST")
    ensemble_detected = sum(r.is_anomaly for r in ensemble_results)
    print(f"Ensemble detected {ensemble_detected} anomalies in 100 samples")
    
    # Print example anomaly
    for result in ensemble_results:
        if result.is_anomaly:
            print(f"\nExample Anomaly Detection:")
            print(f"  Ticker: {result.ticker}")
            print(f"  Anomaly Score: {result.anomaly_score:.3f}")
            print(f"  Confidence: {result.confidence:.2f}%")
            print(f"  Method: {result.method}")
            print(f"  Top Contributing Features:")
            for feature, score in list(result.contributing_features.items())[:3]:
                print(f"    {feature}: {score:.4f}")
            break
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)

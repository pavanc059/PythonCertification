"""
LSTM Neural Network for Time-Series Price Prediction

This module implements LSTM (Long Short-Term Memory) networks for time-series
stock price prediction with uncertainty quantification and cross-validation.

Requirements: 13.1, 13.4, 13.7
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    """
    Data class representing a prediction with uncertainty quantification.
    
    Attributes:
        ticker: Stock ticker symbol
        timestamp: Prediction timestamp
        prediction_type: Type of prediction ('price', 'direction', 'return')
        value: Predicted value (price or return)
        confidence: Confidence score (0-100%)
        lower_bound: Lower bound of 95% confidence interval
        upper_bound: Upper bound of 95% confidence interval
        model_name: Name of the model that generated the prediction
        metadata: Additional metadata (e.g., feature importance, attention weights)
    """
    ticker: str
    timestamp: datetime
    prediction_type: str
    value: float
    confidence: float
    lower_bound: float
    upper_bound: float
    model_name: str = "LSTM"
    metadata: Optional[Dict] = None
    
    def __post_init__(self):
        """Validate prediction data after initialization"""
        if not 0 <= self.confidence <= 100:
            raise ValueError(f"Confidence must be between 0 and 100, got {self.confidence}")
        
        if self.lower_bound > self.upper_bound:
            raise ValueError(f"Lower bound ({self.lower_bound}) cannot be greater than upper bound ({self.upper_bound})")
        
        if not (self.lower_bound <= self.value <= self.upper_bound):
            logger.warning(
                f"Predicted value ({self.value}) is outside confidence interval "
                f"[{self.lower_bound}, {self.upper_bound}]"
            )


class LSTMModel(nn.Module):
    """
    LSTM Neural Network Architecture for Time-Series Prediction.
    
    Architecture:
        Input → LSTM Layer 1 → Dropout → LSTM Layer 2 → Dropout → FC Layer → Output
        
    This is a multi-layer LSTM with dropout regularization to prevent overfitting.
    The model can handle multi-variate time-series input and produces single-step
    ahead predictions.
    """
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        output_size: int = 1
    ):
        """
        Initialize LSTM model.
        
        Args:
            input_size: Number of input features
            hidden_size: Number of hidden units in LSTM layers (default 128)
            num_layers: Number of stacked LSTM layers (default 2)
            dropout: Dropout probability for regularization (default 0.2)
            output_size: Number of output values (default 1)
        """
        super(LSTMModel, self).__init__()
        
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.output_size = output_size
        
        # LSTM layers with dropout between them
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,  # Dropout only between layers
            batch_first=True  # Input shape: (batch, seq, features)
        )
        
        # Dropout layer after LSTM
        self.dropout_layer = nn.Dropout(dropout)
        
        # Fully connected output layer
        self.fc = nn.Linear(hidden_size, output_size)
        
        logger.info(
            f"Initialized LSTM model: input_size={input_size}, hidden_size={hidden_size}, "
            f"num_layers={num_layers}, dropout={dropout}, output_size={output_size}"
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the network.
        
        Args:
            x: Input tensor of shape (batch_size, sequence_length, input_size)
            
        Returns:
            Output tensor of shape (batch_size, output_size)
        """
        # LSTM forward pass
        # lstm_out shape: (batch, seq, hidden_size)
        # h_n shape: (num_layers, batch, hidden_size)
        # c_n shape: (num_layers, batch, hidden_size)
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # Take the output from the last time step
        # Shape: (batch, hidden_size)
        last_output = lstm_out[:, -1, :]
        
        # Apply dropout
        dropped = self.dropout_layer(last_output)
        
        # Fully connected layer to produce final output
        # Shape: (batch, output_size)
        output = self.fc(dropped)
        
        return output


class LSTMPredictor:
    """
    LSTM Predictor for Time-Series Stock Price Prediction.
    
    This class provides a complete interface for training LSTM models on time-series
    stock data with uncertainty quantification and cross-validation.
    
    Features:
    - Multi-layer LSTM architecture with dropout regularization
    - Uncertainty quantification using Monte Carlo Dropout (MC Dropout)
    - 95% confidence intervals for predictions
    - Time-series cross-validation with 5 folds
    - Early stopping to prevent overfitting
    - Learning rate scheduling
    - GPU acceleration support (automatically detects CUDA)
    
    Requirements:
    - Requirement 13.1: LSTM network for time-series price prediction
    - Requirement 13.4: Uncertainty quantification with 95% confidence intervals
    - Requirement 13.7: Time-series cross-validation with 5 folds
    
    Example:
        >>> from stockiq.models.features import create_feature_matrix
        >>> from stockiq.models.preprocessing import preprocess_for_training
        >>> 
        >>> # Create features
        >>> features = create_feature_matrix('AAPL', lookback_days=365)
        >>> X = features.drop(['target_return', 'target_direction'], axis=1)
        >>> y = features['target_return']
        >>> 
        >>> # Preprocess
        >>> data = preprocess_for_training(X, y, test_size=0.2, normalize=True, 
        ...                                 create_sequences_flag=True, sequence_length=60)
        >>> 
        >>> # Train LSTM
        >>> predictor = LSTMPredictor(input_size=X.shape[1])
        >>> predictor.train(data['sequences_train'], data['y_train_seq'], epochs=50)
        >>> 
        >>> # Make predictions
        >>> prediction = predictor.predict(data['sequences_test'][-1:])
        >>> print(f"Predicted return: {prediction.value:.4f} ± {prediction.confidence:.2f}%")
    """
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        learning_rate: float = 0.001,
        device: Optional[str] = None
    ):
        """
        Initialize LSTM Predictor.
        
        Args:
            input_size: Number of input features
            hidden_size: Number of hidden units in LSTM layers (default 128)
            num_layers: Number of stacked LSTM layers (default 2)
            dropout: Dropout probability for regularization (default 0.2)
            learning_rate: Learning rate for Adam optimizer (default 0.001)
            device: Device for computation ('cpu', 'cuda', or None for auto-detect)
        """
        # Detect device (GPU if available, otherwise CPU)
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        logger.info(f"Using device: {self.device}")
        
        # Initialize model
        self.model = LSTMModel(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            output_size=1
        ).to(self.device)
        
        # Optimizer and loss function
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()
        
        # Learning rate scheduler (reduce LR on plateau)
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=5
        )
        
        # Training history
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'learning_rates': []
        }
        
        # Model hyperparameters
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        
        logger.info("LSTM Predictor initialized successfully")
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        epochs: int = 100,
        batch_size: int = 32,
        early_stopping_patience: int = 10,
        verbose: bool = True
    ) -> Dict[str, List[float]]:
        """
        Train the LSTM model on time-series sequences.
        
        Args:
            X_train: Training sequences, shape (num_samples, sequence_length, num_features)
            y_train: Training targets, shape (num_samples,)
            X_val: Validation sequences (optional), same shape as X_train
            y_val: Validation targets (optional), same shape as y_train
            epochs: Maximum number of training epochs (default 100)
            batch_size: Batch size for training (default 32)
            early_stopping_patience: Stop if validation loss doesn't improve for N epochs (default 10)
            verbose: Print training progress (default True)
            
        Returns:
            Dictionary with training history (train_loss, val_loss, learning_rates)
            
        Example:
            >>> predictor = LSTMPredictor(input_size=30)
            >>> history = predictor.train(X_train, y_train, X_val, y_val, epochs=50)
            >>> print(f"Final training loss: {history['train_loss'][-1]:.6f}")
        """
        logger.info(f"Starting LSTM training for {epochs} epochs")
        logger.info(f"Training samples: {len(X_train)}, Batch size: {batch_size}")
        
        if X_val is not None:
            logger.info(f"Validation samples: {len(X_val)}")
        
        # Convert to PyTorch tensors
        X_train_tensor = torch.FloatTensor(X_train).to(self.device)
        y_train_tensor = torch.FloatTensor(y_train).reshape(-1, 1).to(self.device)
        
        if X_val is not None and y_val is not None:
            X_val_tensor = torch.FloatTensor(X_val).to(self.device)
            y_val_tensor = torch.FloatTensor(y_val).reshape(-1, 1).to(self.device)
            use_validation = True
        else:
            use_validation = False
        
        # Early stopping variables
        best_val_loss = float('inf')
        patience_counter = 0
        best_model_state = None
        
        # Training loop
        for epoch in range(epochs):
            # Training phase
            self.model.train()
            train_losses = []
            
            # Mini-batch training
            num_batches = (len(X_train) + batch_size - 1) // batch_size
            
            for i in range(0, len(X_train), batch_size):
                batch_X = X_train_tensor[i:i+batch_size]
                batch_y = y_train_tensor[i:i+batch_size]
                
                # Forward pass
                self.optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = self.criterion(outputs, batch_y)
                
                # Backward pass and optimization
                loss.backward()
                
                # Gradient clipping to prevent exploding gradients
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                
                self.optimizer.step()
                
                train_losses.append(loss.item())
            
            # Calculate average training loss
            avg_train_loss = np.mean(train_losses)
            self.history['train_loss'].append(avg_train_loss)
            self.history['learning_rates'].append(self.optimizer.param_groups[0]['lr'])
            
            # Validation phase
            if use_validation:
                self.model.eval()
                with torch.no_grad():
                    val_outputs = self.model(X_val_tensor)
                    val_loss = self.criterion(val_outputs, y_val_tensor).item()
                    self.history['val_loss'].append(val_loss)
                
                # Learning rate scheduling based on validation loss
                self.scheduler.step(val_loss)
                
                # Early stopping check
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    best_model_state = self.model.state_dict().copy()
                    
                    if verbose:
                        logger.info(f"Epoch {epoch+1}/{epochs} - New best validation loss: {val_loss:.6f}")
                else:
                    patience_counter += 1
                
                # Print progress
                if verbose and (epoch + 1) % 10 == 0:
                    logger.info(
                        f"Epoch {epoch+1}/{epochs} - "
                        f"Train Loss: {avg_train_loss:.6f}, "
                        f"Val Loss: {val_loss:.6f}, "
                        f"LR: {self.optimizer.param_groups[0]['lr']:.6f}"
                    )
                
                # Early stopping
                if patience_counter >= early_stopping_patience:
                    logger.info(f"Early stopping triggered at epoch {epoch+1}")
                    break
            else:
                # No validation - just print training loss
                if verbose and (epoch + 1) % 10 == 0:
                    logger.info(
                        f"Epoch {epoch+1}/{epochs} - "
                        f"Train Loss: {avg_train_loss:.6f}, "
                        f"LR: {self.optimizer.param_groups[0]['lr']:.6f}"
                    )
        
        # Restore best model if using validation
        if use_validation and best_model_state is not None:
            self.model.load_state_dict(best_model_state)
            logger.info(f"Restored best model with validation loss: {best_val_loss:.6f}")
        
        logger.info("Training completed")
        return self.history
    
    def predict(
        self,
        X: np.ndarray,
        n_iterations: int = 100,
        ticker: str = "UNKNOWN",
        prediction_type: str = "return"
    ) -> Prediction:
        """
        Generate prediction with uncertainty quantification using Monte Carlo Dropout.
        
        This method uses MC Dropout to estimate uncertainty:
        1. Keep dropout enabled during inference
        2. Make multiple forward passes (n_iterations)
        3. Collect predictions to estimate mean and variance
        4. Calculate 95% confidence intervals
        
        Args:
            X: Input sequence, shape (1, sequence_length, num_features) or 
               (sequence_length, num_features)
            n_iterations: Number of MC Dropout iterations for uncertainty estimation (default 100)
            ticker: Stock ticker symbol for the prediction
            prediction_type: Type of prediction ('price', 'return', 'direction')
            
        Returns:
            Prediction object with value, confidence intervals, and metadata
            
        Example:
            >>> prediction = predictor.predict(test_sequence)
            >>> print(f"Prediction: {prediction.value:.4f}")
            >>> print(f"95% CI: [{prediction.lower_bound:.4f}, {prediction.upper_bound:.4f}]")
            >>> print(f"Confidence: {prediction.confidence:.2f}%")
        """
        # Ensure X has batch dimension
        if len(X.shape) == 2:
            X = X.reshape(1, X.shape[0], X.shape[1])
        
        # Convert to tensor
        X_tensor = torch.FloatTensor(X).to(self.device)
        
        # Enable dropout for MC Dropout
        self.model.train()  # This enables dropout layers
        
        # Collect predictions from multiple forward passes
        predictions = []
        
        with torch.no_grad():
            for _ in range(n_iterations):
                output = self.model(X_tensor)
                predictions.append(output.cpu().numpy()[0, 0])
        
        # Calculate statistics
        predictions = np.array(predictions)
        mean_prediction = np.mean(predictions)
        std_prediction = np.std(predictions)
        
        # Calculate 95% confidence interval (1.96 standard deviations)
        lower_bound = mean_prediction - 1.96 * std_prediction
        upper_bound = mean_prediction + 1.96 * std_prediction
        
        # Calculate confidence score (0-100%)
        # Lower standard deviation = higher confidence
        # We use coefficient of variation (CV) to normalize by prediction magnitude
        cv = abs(std_prediction / (mean_prediction + 1e-8))  # Add epsilon to avoid division by zero
        confidence = max(0, min(100, 100 * (1 - cv)))  # Clamp to [0, 100]
        
        # Create prediction object
        prediction = Prediction(
            ticker=ticker,
            timestamp=datetime.now(),
            prediction_type=prediction_type,
            value=float(mean_prediction),
            confidence=float(confidence),
            lower_bound=float(lower_bound),
            upper_bound=float(upper_bound),
            model_name="LSTM",
            metadata={
                'mc_iterations': n_iterations,
                'std_deviation': float(std_prediction),
                'coefficient_variation': float(cv),
                'prediction_distribution': predictions.tolist()[:10]  # Store first 10 samples
            }
        )
        
        logger.info(
            f"Prediction generated - Value: {mean_prediction:.6f}, "
            f"Std: {std_prediction:.6f}, Confidence: {confidence:.2f}%"
        )
        
        return prediction
    
    def cross_validate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_splits: int = 5,
        epochs: int = 50,
        batch_size: int = 32,
        verbose: bool = True
    ) -> Dict[str, List[float]]:
        """
        Perform time-series cross-validation with 5 folds.
        
        Time-series CV uses expanding window:
        - Fold 1: Train on 20%, test on next 16%
        - Fold 2: Train on 36%, test on next 16%
        - Fold 3: Train on 52%, test on next 16%
        - Fold 4: Train on 68%, test on next 16%
        - Fold 5: Train on 84%, test on final 16%
        
        Requirements: 13.7 - Time-series cross-validation with 5 folds
        
        Args:
            X: Input sequences, shape (num_samples, sequence_length, num_features)
            y: Target values, shape (num_samples,)
            n_splits: Number of CV folds (default 5)
            epochs: Training epochs per fold (default 50)
            batch_size: Batch size for training (default 32)
            verbose: Print progress (default True)
            
        Returns:
            Dictionary with fold scores and metrics:
            - fold_losses: List of validation losses for each fold
            - fold_accuracies: List of directional accuracies for each fold
            - mean_loss: Average validation loss across folds
            - std_loss: Standard deviation of validation losses
            - mean_accuracy: Average directional accuracy across folds
            
        Example:
            >>> results = predictor.cross_validate(X, y, n_splits=5, epochs=30)
            >>> print(f"Mean CV Loss: {results['mean_loss']:.6f} ± {results['std_loss']:.6f}")
            >>> print(f"Mean CV Accuracy: {results['mean_accuracy']:.2f}%")
        """
        logger.info(f"Starting {n_splits}-fold time-series cross-validation")
        logger.info(f"Total samples: {len(X)}, Epochs per fold: {epochs}")
        
        # Calculate fold sizes for expanding window
        total_samples = len(X)
        test_size = total_samples // (n_splits + 1)  # Size of each test fold
        
        fold_losses = []
        fold_accuracies = []
        fold_predictions = []
        
        for fold in range(n_splits):
            if verbose:
                logger.info(f"\n{'='*60}")
                logger.info(f"Fold {fold + 1}/{n_splits}")
                logger.info(f"{'='*60}")
            
            # Calculate train/test split indices (expanding window)
            train_end = (fold + 1) * test_size + (fold * test_size)
            test_start = train_end
            test_end = test_start + test_size
            
            # Ensure we don't exceed array bounds and have reasonable test size
            test_end = min(test_end, total_samples)
            
            # Skip fold if test set would be empty or too small
            if test_start >= test_end or (test_end - test_start) < 5:
                if verbose:
                    logger.warning(f"Skipping fold {fold + 1}: insufficient test data")
                continue
            
            # Split data
            X_train_fold = X[:train_end]
            y_train_fold = y[:train_end]
            X_test_fold = X[test_start:test_end]
            y_test_fold = y[test_start:test_end]
            
            if verbose:
                logger.info(f"Train samples: {len(X_train_fold)} (0:{train_end})")
                logger.info(f"Test samples: {len(X_test_fold)} ({test_start}:{test_end})")
            
            # Reset model for this fold
            self.model = LSTMModel(
                input_size=self.input_size,
                hidden_size=self.hidden_size,
                num_layers=self.num_layers,
                dropout=self.dropout,
                output_size=1
            ).to(self.device)
            
            self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
            self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                self.optimizer, mode='min', factor=0.5, patience=5
            )
            
            # Train on this fold
            self.train(
                X_train_fold, y_train_fold,
                X_test_fold, y_test_fold,
                epochs=epochs,
                batch_size=batch_size,
                early_stopping_patience=10,
                verbose=verbose
            )
            
            # Evaluate on test fold
            self.model.eval()
            with torch.no_grad():
                X_test_tensor = torch.FloatTensor(X_test_fold).to(self.device)
                y_test_tensor = torch.FloatTensor(y_test_fold).reshape(-1, 1)
                
                predictions = self.model(X_test_tensor).cpu().numpy().flatten()
                
                # Calculate loss
                fold_loss = float(np.mean((predictions - y_test_fold) ** 2))
                fold_losses.append(fold_loss)
                
                # Calculate directional accuracy
                pred_direction = (predictions > 0).astype(int)
                true_direction = (y_test_fold > 0).astype(int)
                fold_accuracy = float(np.mean(pred_direction == true_direction) * 100)
                fold_accuracies.append(fold_accuracy)
                
                fold_predictions.append({
                    'predictions': predictions,
                    'actuals': y_test_fold,
                    'loss': fold_loss,
                    'accuracy': fold_accuracy
                })
            
            if verbose:
                logger.info(f"Fold {fold + 1} Results:")
                logger.info(f"  Loss: {fold_loss:.6f}")
                logger.info(f"  Directional Accuracy: {fold_accuracy:.2f}%")
        
        # Calculate summary statistics
        results = {
            'fold_losses': fold_losses,
            'fold_accuracies': fold_accuracies,
            'mean_loss': float(np.mean(fold_losses)),
            'std_loss': float(np.std(fold_losses)),
            'mean_accuracy': float(np.mean(fold_accuracies)),
            'std_accuracy': float(np.std(fold_accuracies)),
            'fold_predictions': fold_predictions
        }
        
        if verbose:
            logger.info(f"\n{'='*60}")
            logger.info("Cross-Validation Summary")
            logger.info(f"{'='*60}")
            logger.info(f"Mean Loss: {results['mean_loss']:.6f} ± {results['std_loss']:.6f}")
            logger.info(f"Mean Directional Accuracy: {results['mean_accuracy']:.2f}% ± {results['std_accuracy']:.2f}%")
            logger.info(f"{'='*60}\n")
        
        return results
    
    def save_model(self, path: str) -> None:
        """
        Save model state to disk.
        
        Args:
            path: File path to save model (e.g., 'models/lstm_aapl.pth')
        """
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'history': self.history,
            'hyperparameters': {
                'input_size': self.input_size,
                'hidden_size': self.hidden_size,
                'num_layers': self.num_layers,
                'dropout': self.dropout,
                'learning_rate': self.learning_rate
            }
        }, path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str) -> None:
        """
        Load model state from disk.
        
        Args:
            path: File path to load model from
        """
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.history = checkpoint['history']
        
        logger.info(f"Model loaded from {path}")


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    print("\nLSTM Predictor - Example Usage\n")
    print("=" * 60)
    
    # Create synthetic time-series data for testing
    print("\n1. Creating synthetic time-series data...")
    np.random.seed(42)
    torch.manual_seed(42)
    
    num_samples = 500
    sequence_length = 60
    num_features = 10
    
    # Generate synthetic sequences
    X = np.random.randn(num_samples, sequence_length, num_features).astype(np.float32)
    y = np.random.randn(num_samples).astype(np.float32)
    
    print(f"Data shape: X={X.shape}, y={y.shape}")
    
    # Split into train/test
    split_idx = int(0.8 * num_samples)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"Train: X={X_train.shape}, y={y_train.shape}")
    print(f"Test: X={X_test.shape}, y={y_test.shape}")
    
    # Initialize predictor
    print("\n2. Initializing LSTM Predictor...")
    predictor = LSTMPredictor(
        input_size=num_features,
        hidden_size=64,
        num_layers=2,
        dropout=0.2,
        learning_rate=0.001
    )
    
    # Train model
    print("\n3. Training LSTM model...")
    history = predictor.train(
        X_train, y_train,
        X_test, y_test,
        epochs=20,
        batch_size=32,
        early_stopping_patience=5,
        verbose=True
    )
    
    print(f"\nTraining completed:")
    print(f"  Final train loss: {history['train_loss'][-1]:.6f}")
    print(f"  Final val loss: {history['val_loss'][-1]:.6f}")
    
    # Make predictions with uncertainty quantification
    print("\n4. Making predictions with uncertainty quantification...")
    test_sequence = X_test[0:1]  # Take first test sample
    prediction = predictor.predict(
        test_sequence,
        n_iterations=100,
        ticker="TEST",
        prediction_type="return"
    )
    
    print(f"\nPrediction Results:")
    print(f"  Ticker: {prediction.ticker}")
    print(f"  Predicted value: {prediction.value:.6f}")
    print(f"  Confidence: {prediction.confidence:.2f}%")
    print(f"  95% CI: [{prediction.lower_bound:.6f}, {prediction.upper_bound:.6f}]")
    print(f"  Actual value: {y_test[0]:.6f}")
    
    # Cross-validation
    print("\n5. Performing 5-fold time-series cross-validation...")
    cv_results = predictor.cross_validate(
        X_train, y_train,
        n_splits=5,
        epochs=10,
        batch_size=32,
        verbose=True
    )
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)

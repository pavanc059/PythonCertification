"""
Transformer Model for Multi-Variate Market Analysis

This module implements Transformer-based neural networks for multi-variate
stock market prediction with attention weight visualization for explainability.

Requirements: 13.2
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from datetime import datetime
import logging
import math

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
        metadata: Additional metadata (e.g., attention weights, feature importance)
    """
    ticker: str
    timestamp: datetime
    prediction_type: str
    value: float
    confidence: float
    lower_bound: float
    upper_bound: float
    model_name: str = "Transformer"
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


class PositionalEncoding(nn.Module):
    """
    Positional Encoding for Transformer Architecture.
    
    Injects information about the relative or absolute position of tokens
    in the sequence using sine and cosine functions of different frequencies.
    """
    
    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        """
        Initialize positional encoding.
        
        Args:
            d_model: Dimension of the model (embedding size)
            max_len: Maximum sequence length (default 5000)
            dropout: Dropout probability (default 0.1)
        """
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        # Create positional encoding matrix
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        
        # Apply sine to even indices and cosine to odd indices
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term[:pe[:, 1::2].size(1)])
        
        # Add batch dimension: (max_len, d_model) -> (1, max_len, d_model)
        pe = pe.unsqueeze(0)
        
        # Register as buffer (not a parameter, but part of state)
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Add positional encoding to input.
        
        Args:
            x: Input tensor of shape (batch_size, seq_length, d_model)
            
        Returns:
            Tensor with positional encoding added, same shape as input
        """
        # Add positional encoding to input
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


class TransformerModel(nn.Module):
    """
    Transformer Neural Network Architecture for Multi-Variate Market Analysis.
    
    Architecture:
        Input → Embedding → Positional Encoding → 
        Transformer Encoder Layers → Global Average Pool → 
        Dropout → FC Layer → Output
        
    This model uses multi-head self-attention to capture complex relationships
    between different market features and time steps. Attention weights can be
    extracted for explainability.
    """
    
    def __init__(
        self,
        input_size: int,
        d_model: int = 128,
        nhead: int = 8,
        num_layers: int = 4,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
        output_size: int = 1
    ):
        """
        Initialize Transformer model.
        
        Args:
            input_size: Number of input features
            d_model: Dimension of model embeddings (default 128)
            nhead: Number of attention heads (default 8)
            num_layers: Number of transformer encoder layers (default 4)
            dim_feedforward: Dimension of feedforward network (default 512)
            dropout: Dropout probability (default 0.1)
            output_size: Number of output values (default 1)
        """
        super(TransformerModel, self).__init__()
        
        self.input_size = input_size
        self.d_model = d_model
        self.nhead = nhead
        self.num_layers = num_layers
        self.dim_feedforward = dim_feedforward
        self.dropout = dropout
        self.output_size = output_size
        
        # Input embedding layer (project input features to d_model dimensions)
        self.input_embedding = nn.Linear(input_size, d_model)
        
        # Positional encoding
        self.pos_encoder = PositionalEncoding(d_model, dropout=dropout)
        
        # Transformer encoder layers
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True  # Input shape: (batch, seq, features)
        )
        
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )
        
        # Dropout layer
        self.dropout_layer = nn.Dropout(dropout)
        
        # Output layer (maps from d_model to output_size)
        self.fc = nn.Linear(d_model, output_size)
        
        # Store attention weights for explainability
        self.attention_weights = None
        
        logger.info(
            f"Initialized Transformer model: input_size={input_size}, d_model={d_model}, "
            f"nhead={nhead}, num_layers={num_layers}, dim_feedforward={dim_feedforward}, "
            f"dropout={dropout}, output_size={output_size}"
        )
    
    def forward(self, x: torch.Tensor, return_attention: bool = False) -> torch.Tensor:
        """
        Forward pass through the network.
        
        Args:
            x: Input tensor of shape (batch_size, sequence_length, input_size)
            return_attention: Whether to store attention weights for visualization
            
        Returns:
            Output tensor of shape (batch_size, output_size)
        """
        # Embed input features to d_model dimensions
        # Shape: (batch, seq, input_size) -> (batch, seq, d_model)
        x = self.input_embedding(x)
        
        # Add positional encoding
        x = self.pos_encoder(x)
        
        # Transformer encoder
        # Shape: (batch, seq, d_model) -> (batch, seq, d_model)
        if return_attention:
            # Manually iterate through layers to extract attention weights
            attention_weights = []
            for layer in self.transformer_encoder.layers:
                # Forward pass through attention layer
                x_attended, attn_weight = layer.self_attn(x, x, x, need_weights=True, average_attn_weights=True)
                attention_weights.append(attn_weight.detach().cpu())
                
                # Complete the layer forward pass (residual, norm, feedforward)
                x = layer.norm1(x + layer.dropout1(x_attended))
                x = layer.norm2(x + layer.dropout2(layer.linear2(layer.dropout(layer.activation(layer.linear1(x))))))
            
            self.attention_weights = attention_weights
        else:
            x = self.transformer_encoder(x)
        
        # Global average pooling across sequence dimension
        # Shape: (batch, seq, d_model) -> (batch, d_model)
        x = torch.mean(x, dim=1)
        
        # Apply dropout
        x = self.dropout_layer(x)
        
        # Fully connected output layer
        # Shape: (batch, d_model) -> (batch, output_size)
        output = self.fc(x)
        
        return output
    
    def get_attention_weights(self) -> Optional[List[torch.Tensor]]:
        """
        Get stored attention weights from the last forward pass.
        
        Returns:
            List of attention weight tensors, one per layer, or None if not computed
        """
        return self.attention_weights


class TransformerPredictor:
    """
    Transformer Predictor for Multi-Variate Market Analysis.
    
    This class provides a complete interface for training Transformer models
    on multi-variate stock market data with attention weight visualization
    for explainability.
    
    Features:
    - Multi-head self-attention mechanism for capturing complex relationships
    - Positional encoding for sequence order information
    - Attention weight extraction for explainability
    - Uncertainty quantification using Monte Carlo Dropout
    - 95% confidence intervals for predictions
    - Time-series cross-validation with 5 folds
    - Early stopping and learning rate scheduling
    - GPU acceleration support
    
    Requirements:
    - Requirement 13.2: Transformer model for multi-variate market analysis
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
        >>> # Train Transformer
        >>> predictor = TransformerPredictor(input_size=X.shape[1])
        >>> predictor.train(data['sequences_train'], data['y_train_seq'], epochs=50)
        >>> 
        >>> # Make predictions with attention visualization
        >>> prediction = predictor.predict(data['sequences_test'][-1:], 
        ...                               return_attention=True)
        >>> print(f"Predicted return: {prediction.value:.4f} ± {prediction.confidence:.2f}%")
        >>> 
        >>> # Visualize attention weights
        >>> attention = prediction.metadata['attention_weights']
        >>> predictor.visualize_attention(attention[0], feature_names=X.columns)
    """
    
    def __init__(
        self,
        input_size: int,
        d_model: int = 128,
        nhead: int = 8,
        num_layers: int = 4,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
        learning_rate: float = 0.0001,
        device: Optional[str] = None
    ):
        """
        Initialize Transformer Predictor.
        
        Args:
            input_size: Number of input features
            d_model: Dimension of model embeddings (default 128)
            nhead: Number of attention heads (default 8)
            num_layers: Number of transformer encoder layers (default 4)
            dim_feedforward: Dimension of feedforward network (default 512)
            dropout: Dropout probability (default 0.1)
            learning_rate: Learning rate for Adam optimizer (default 0.0001)
            device: Device for computation ('cpu', 'cuda', or None for auto-detect)
        """
        # Detect device (GPU if available, otherwise CPU)
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        logger.info(f"Using device: {self.device}")
        
        # Initialize model
        self.model = TransformerModel(
            input_size=input_size,
            d_model=d_model,
            nhead=nhead,
            num_layers=num_layers,
            dim_feedforward=dim_feedforward,
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
        self.d_model = d_model
        self.nhead = nhead
        self.num_layers = num_layers
        self.dim_feedforward = dim_feedforward
        self.dropout = dropout
        self.learning_rate = learning_rate
        
        logger.info("Transformer Predictor initialized successfully")
    
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
        Train the Transformer model on time-series sequences.
        
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
        """
        logger.info(f"Starting Transformer training for {epochs} epochs")
        logger.info(f"Training samples: {len(X_train)}, Batch size: {batch_size}")
        
        if X_val is not None:
            logger.info(f"Validation samples: {len(X_val)}")
        
        # Convert to PyTorch tensors
        X_train_tensor = torch.FloatTensor(X_train).to(self.device)
        y_train_tensor = torch.FloatTensor(y_train).reshape(-1, 1).to(self.device)
        
        if X_val is not None and y_val is not None:
            X_val_tensor = torch.FloatTensor(X_val).to(self.device)
            y_val_tensor = torch.FloatTensor(y_val).reshape(-1, 1)
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
                
                # Learning rate scheduling
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
        prediction_type: str = "return",
        return_attention: bool = False
    ) -> Prediction:
        """
        Generate prediction with uncertainty quantification and attention weights.
        
        Uses Monte Carlo Dropout for uncertainty estimation:
        1. Keep dropout enabled during inference
        2. Make multiple forward passes (n_iterations)
        3. Collect predictions to estimate mean and variance
        4. Calculate 95% confidence intervals
        5. Optionally extract attention weights for explainability
        
        Args:
            X: Input sequence, shape (1, sequence_length, num_features) or
               (sequence_length, num_features)
            n_iterations: Number of MC Dropout iterations (default 100)
            ticker: Stock ticker symbol for the prediction
            prediction_type: Type of prediction ('price', 'return', 'direction')
            return_attention: Whether to extract attention weights for visualization
            
        Returns:
            Prediction object with value, confidence intervals, and optional attention weights
        """
        # Ensure X has batch dimension
        if len(X.shape) == 2:
            X = X.reshape(1, X.shape[0], X.shape[1])
        
        # Convert to tensor
        X_tensor = torch.FloatTensor(X).to(self.device)
        
        # Enable dropout for MC Dropout
        self.model.train()
        
        # Collect predictions from multiple forward passes
        predictions = []
        attention_weights = None
        
        with torch.no_grad():
            for i in range(n_iterations):
                # Get attention weights only on first iteration if requested
                if return_attention and i == 0:
                    output = self.model(X_tensor, return_attention=True)
                    attention_weights = self.model.get_attention_weights()
                else:
                    output = self.model(X_tensor, return_attention=False)
                
                predictions.append(output.cpu().numpy()[0, 0])
        
        # Calculate statistics
        predictions = np.array(predictions)
        mean_prediction = np.mean(predictions)
        std_prediction = np.std(predictions)
        
        # Calculate 95% confidence interval
        lower_bound = mean_prediction - 1.96 * std_prediction
        upper_bound = mean_prediction + 1.96 * std_prediction
        
        # Calculate confidence score (0-100%)
        cv = abs(std_prediction / (mean_prediction + 1e-8))
        confidence = max(0, min(100, 100 * (1 - cv)))
        
        # Prepare metadata
        metadata = {
            'mc_iterations': n_iterations,
            'std_deviation': float(std_prediction),
            'coefficient_variation': float(cv),
            'prediction_distribution': predictions.tolist()[:10]
        }
        
        # Add attention weights if requested
        if return_attention and attention_weights is not None:
            metadata['attention_weights'] = [w.numpy() for w in attention_weights]
            metadata['num_layers'] = len(attention_weights)
            metadata['attention_shape'] = attention_weights[0].shape
        
        # Create prediction object
        prediction = Prediction(
            ticker=ticker,
            timestamp=datetime.now(),
            prediction_type=prediction_type,
            value=float(mean_prediction),
            confidence=float(confidence),
            lower_bound=float(lower_bound),
            upper_bound=float(upper_bound),
            model_name="Transformer",
            metadata=metadata
        )
        
        logger.info(
            f"Prediction generated - Value: {mean_prediction:.6f}, "
            f"Std: {std_prediction:.6f}, Confidence: {confidence:.2f}%"
        )
        
        if return_attention:
            logger.info(f"Attention weights extracted from {len(attention_weights)} layers")
        
        return prediction
    
    def visualize_attention(
        self,
        attention_weights: np.ndarray,
        feature_names: Optional[List[str]] = None,
        save_path: Optional[str] = None
    ) -> None:
        """
        Visualize attention weights as a heatmap for explainability.
        
        Args:
            attention_weights: Attention weights from one layer, shape (seq_length, seq_length)
            feature_names: Optional list of feature names for axis labels
            save_path: Optional path to save the visualization
        """
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
        except ImportError:
            logger.error("matplotlib and seaborn required for visualization")
            return
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create heatmap
        sns.heatmap(
            attention_weights,
            cmap='viridis',
            ax=ax,
            cbar_kws={'label': 'Attention Weight'}
        )
        
        ax.set_title('Transformer Attention Weights Heatmap', fontsize=14, fontweight='bold')
        ax.set_xlabel('Key Position (Time Step)', fontsize=12)
        ax.set_ylabel('Query Position (Time Step)', fontsize=12)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Attention visualization saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def visualize_attention_by_feature(
        self,
        attention_weights: np.ndarray,
        input_sequence: np.ndarray,
        feature_names: List[str],
        save_path: Optional[str] = None
    ) -> None:
        """
        Visualize which time steps the model attends to for each feature.
        
        Args:
            attention_weights: Attention weights, shape (seq_length, seq_length)
            input_sequence: Input sequence, shape (seq_length, num_features)
            feature_names: List of feature names
            save_path: Optional path to save the visualization
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.error("matplotlib required for visualization")
            return
        
        # Calculate average attention across all positions for each time step
        avg_attention = attention_weights.mean(axis=0)  # Shape: (seq_length,)
        
        # Create figure with subplots
        num_features = len(feature_names)
        fig, axes = plt.subplots(num_features, 1, figsize=(12, 2 * num_features))
        
        if num_features == 1:
            axes = [axes]
        
        # Plot each feature with attention overlay
        for i, (ax, feature_name) in enumerate(zip(axes, feature_names)):
            # Plot feature values
            ax.plot(input_sequence[:, i], label=feature_name, color='blue', linewidth=2)
            
            # Overlay attention weights as transparency
            ax2 = ax.twinx()
            ax2.fill_between(
                range(len(avg_attention)),
                avg_attention,
                alpha=0.3,
                color='red',
                label='Attention'
            )
            
            ax.set_xlabel('Time Step')
            ax.set_ylabel(feature_name, color='blue')
            ax2.set_ylabel('Attention Weight', color='red')
            ax.tick_params(axis='y', labelcolor='blue')
            ax2.tick_params(axis='y', labelcolor='red')
            ax.grid(True, alpha=0.3)
        
        plt.suptitle('Feature Values with Attention Weights', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Feature attention visualization saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
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
        
        Requirements: 13.7 - Time-series cross-validation with 5 folds
        
        Args:
            X: Input sequences, shape (num_samples, sequence_length, num_features)
            y: Target values, shape (num_samples,)
            n_splits: Number of CV folds (default 5)
            epochs: Training epochs per fold (default 50)
            batch_size: Batch size for training (default 32)
            verbose: Print progress (default True)
            
        Returns:
            Dictionary with fold scores and metrics
        """
        logger.info(f"Starting {n_splits}-fold time-series cross-validation")
        logger.info(f"Total samples: {len(X)}, Epochs per fold: {epochs}")
        
        # Calculate fold sizes for expanding window
        total_samples = len(X)
        test_size = total_samples // (n_splits + 1)
        
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
            
            # Ensure we don't exceed array bounds
            test_end = min(test_end, total_samples)
            
            # Skip fold if test set would be too small
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
            self.model = TransformerModel(
                input_size=self.input_size,
                d_model=self.d_model,
                nhead=self.nhead,
                num_layers=self.num_layers,
                dim_feedforward=self.dim_feedforward,
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
            path: File path to save model
        """
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'history': self.history,
            'hyperparameters': {
                'input_size': self.input_size,
                'd_model': self.d_model,
                'nhead': self.nhead,
                'num_layers': self.num_layers,
                'dim_feedforward': self.dim_feedforward,
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
    
    print("\nTransformer Predictor - Example Usage\n")
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
    print("\n2. Initializing Transformer Predictor...")
    predictor = TransformerPredictor(
        input_size=num_features,
        d_model=64,
        nhead=4,
        num_layers=2,
        dim_feedforward=256,
        dropout=0.1,
        learning_rate=0.0001
    )
    
    # Train model
    print("\n3. Training Transformer model...")
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
    
    # Make predictions with uncertainty quantification and attention weights
    print("\n4. Making predictions with attention visualization...")
    test_sequence = X_test[0:1]
    prediction = predictor.predict(
        test_sequence,
        n_iterations=100,
        ticker="TEST",
        prediction_type="return",
        return_attention=True
    )
    
    print(f"\nPrediction Results:")
    print(f"  Ticker: {prediction.ticker}")
    print(f"  Predicted value: {prediction.value:.6f}")
    print(f"  Confidence: {prediction.confidence:.2f}%")
    print(f"  95% CI: [{prediction.lower_bound:.6f}, {prediction.upper_bound:.6f}]")
    print(f"  Actual value: {y_test[0]:.6f}")
    
    # Check attention weights
    if 'attention_weights' in prediction.metadata:
        attention = prediction.metadata['attention_weights']
        print(f"\nAttention Weights:")
        print(f"  Number of layers: {len(attention)}")
        print(f"  Shape per layer: {attention[0].shape}")
        print(f"  First layer average attention: {attention[0].mean():.6f}")
        
        # Visualize attention from first layer
        print("\n5. Visualizing attention weights...")
        try:
            predictor.visualize_attention(
                attention[0][0],  # First sample, first layer
                save_path="transformer_attention_heatmap.png"
            )
            print("  Attention heatmap saved to transformer_attention_heatmap.png")
        except Exception as e:
            print(f"  Visualization skipped: {e}")
    
    # Cross-validation
    print("\n6. Performing 5-fold time-series cross-validation...")
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

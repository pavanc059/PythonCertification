"""
TransformerPredictor Demo

Demonstrates the usage of TransformerPredictor for multi-variate market analysis
with attention weight visualization.

Usage:
    python examples/transformer_demo.py

Requirements: 13.2
"""

import numpy as np
import torch
import logging
from stockiq.models.deep.transformer import TransformerPredictor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_synthetic_market_data(num_samples=500, sequence_length=60, num_features=10):
    """
    Create synthetic market data for demonstration.
    
    In production, use stockiq.models.features.create_feature_matrix() to generate
    real features from market data.
    """
    np.random.seed(42)
    torch.manual_seed(42)
    
    # Generate synthetic sequences with some temporal structure
    X = np.zeros((num_samples, sequence_length, num_features))
    y = np.zeros(num_samples)
    
    for i in range(num_samples):
        # Create correlated features with time dependencies
        trend = np.linspace(0, np.random.randn(), sequence_length)
        for f in range(num_features):
            X[i, :, f] = trend + np.random.randn(sequence_length) * 0.5
        
        # Target is influenced by recent trend
        y[i] = np.mean(X[i, -5:, :]) + np.random.randn() * 0.1
    
    return X.astype(np.float32), y.astype(np.float32)


def demo_basic_training():
    """Demonstrate basic training workflow"""
    logger.info("="*60)
    logger.info("DEMO 1: Basic Training and Prediction")
    logger.info("="*60)
    
    # Create data
    logger.info("\n1. Creating synthetic market data...")
    X, y = create_synthetic_market_data(num_samples=500, sequence_length=60, num_features=10)
    
    # Split
    split_idx = int(0.8 * len(X))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    logger.info(f"   Train: {X_train.shape[0]} samples")
    logger.info(f"   Test: {X_test.shape[0]} samples")
    
    # Initialize predictor
    logger.info("\n2. Initializing TransformerPredictor...")
    predictor = TransformerPredictor(
        input_size=10,
        d_model=64,
        nhead=4,
        num_layers=2,
        dim_feedforward=256,
        dropout=0.1,
        learning_rate=0.0001
    )
    
    # Train
    logger.info("\n3. Training model...")
    history = predictor.train(
        X_train, y_train,
        X_test, y_test,
        epochs=20,
        batch_size=32,
        early_stopping_patience=5,
        verbose=True
    )
    
    logger.info(f"\n   Training completed!")
    logger.info(f"   Final train loss: {history['train_loss'][-1]:.6f}")
    logger.info(f"   Final val loss: {history['val_loss'][-1]:.6f}")
    logger.info(f"   Training epochs: {len(history['train_loss'])}")
    
    return predictor, X_test, y_test


def demo_uncertainty_quantification(predictor, X_test, y_test):
    """Demonstrate uncertainty quantification with MC Dropout"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 2: Uncertainty Quantification")
    logger.info("="*60)
    
    logger.info("\nMaking predictions with Monte Carlo Dropout...")
    
    # Make predictions on first 5 test samples
    predictions = []
    for i in range(min(5, len(X_test))):
        prediction = predictor.predict(
            X_test[i:i+1],
            n_iterations=100,
            ticker=f"STOCK_{i}",
            prediction_type="return"
        )
        predictions.append(prediction)
        
        logger.info(f"\nStock {i+1}:")
        logger.info(f"   Predicted: {prediction.value:.6f}")
        logger.info(f"   Actual: {y_test[i]:.6f}")
        logger.info(f"   Error: {abs(prediction.value - y_test[i]):.6f}")
        logger.info(f"   Confidence: {prediction.confidence:.2f}%")
        logger.info(f"   95% CI: [{prediction.lower_bound:.6f}, {prediction.upper_bound:.6f}]")
        logger.info(f"   Std Dev: {prediction.metadata['std_deviation']:.6f}")


def demo_attention_extraction(predictor, X_test):
    """Demonstrate attention weight extraction"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 3: Attention Weight Extraction")
    logger.info("="*60)
    
    logger.info("\nExtracting attention weights...")
    
    # Predict with attention
    prediction = predictor.predict(
        X_test[0:1],
        n_iterations=50,
        ticker="DEMO_STOCK",
        return_attention=True
    )
    
    if 'attention_weights' in prediction.metadata:
        attention = prediction.metadata['attention_weights']
        
        logger.info(f"\nAttention Weights Extracted:")
        logger.info(f"   Number of layers: {len(attention)}")
        logger.info(f"   Shape per layer: {attention[0].shape}")
        logger.info(f"   First layer shape: (batch={attention[0].shape[0]}, "
                   f"seq_length={attention[0].shape[1]}, seq_length={attention[0].shape[2]})")
        
        # Analyze attention patterns
        for layer_idx, layer_attention in enumerate(attention):
            avg_attention = layer_attention[0].mean()
            max_attention = layer_attention[0].max()
            min_attention = layer_attention[0].min()
            
            logger.info(f"\n   Layer {layer_idx + 1} Statistics:")
            logger.info(f"      Mean attention: {avg_attention:.4f}")
            logger.info(f"      Max attention: {max_attention:.4f}")
            logger.info(f"      Min attention: {min_attention:.4f}")
        
        # Optionally visualize (requires matplotlib)
        try:
            logger.info("\n   Saving attention visualization...")
            predictor.visualize_attention(
                attention[0][0],  # First sample, first layer
                save_path="transformer_attention_demo.png"
            )
            logger.info("   Attention heatmap saved to: transformer_attention_demo.png")
        except Exception as e:
            logger.warning(f"   Could not create visualization: {e}")
    else:
        logger.warning("   No attention weights found in prediction metadata")


def demo_cross_validation(X, y):
    """Demonstrate 5-fold time-series cross-validation"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 4: Time-Series Cross-Validation")
    logger.info("="*60)
    
    logger.info("\nPerforming 5-fold cross-validation...")
    logger.info("(Using smaller model for faster execution)")
    
    # Use smaller model for faster CV
    predictor = TransformerPredictor(
        input_size=10,
        d_model=32,
        nhead=4,
        num_layers=2,
        dim_feedforward=128,
        dropout=0.1
    )
    
    # Use subset of data for faster demo
    X_subset = X[:300]
    y_subset = y[:300]
    
    cv_results = predictor.cross_validate(
        X_subset, y_subset,
        n_splits=3,  # Using 3 folds for faster demo
        epochs=10,
        batch_size=32,
        verbose=False
    )
    
    logger.info(f"\nCross-Validation Results:")
    logger.info(f"   Fold Losses: {[f'{loss:.6f}' for loss in cv_results['fold_losses']]}")
    logger.info(f"   Fold Accuracies: {[f'{acc:.2f}%' for acc in cv_results['fold_accuracies']]}")
    logger.info(f"   Mean Loss: {cv_results['mean_loss']:.6f} ± {cv_results['std_loss']:.6f}")
    logger.info(f"   Mean Accuracy: {cv_results['mean_accuracy']:.2f}% ± {cv_results['std_accuracy']:.2f}%")


def demo_model_persistence(predictor):
    """Demonstrate model saving and loading"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 5: Model Persistence")
    logger.info("="*60)
    
    # Save model
    model_path = "transformer_model_demo.pth"
    logger.info(f"\nSaving model to: {model_path}")
    predictor.save_model(model_path)
    logger.info("   Model saved successfully")
    
    # Load model
    logger.info(f"\nLoading model from: {model_path}")
    new_predictor = TransformerPredictor(
        input_size=10,
        d_model=64,
        nhead=4,
        num_layers=2
    )
    new_predictor.load_model(model_path)
    logger.info("   Model loaded successfully")
    logger.info(f"   Training history entries: {len(new_predictor.history['train_loss'])}")


def main():
    """Run all demos"""
    logger.info("\n" + "="*60)
    logger.info("TransformerPredictor Demonstration")
    logger.info("Multi-Variate Market Analysis with Attention")
    logger.info("="*60)
    
    # Generate data once
    X, y = create_synthetic_market_data(num_samples=500, sequence_length=60, num_features=10)
    
    # Demo 1: Basic training
    predictor, X_test, y_test = demo_basic_training()
    
    # Demo 2: Uncertainty quantification
    demo_uncertainty_quantification(predictor, X_test, y_test)
    
    # Demo 3: Attention extraction
    demo_attention_extraction(predictor, X_test)
    
    # Demo 4: Cross-validation
    demo_cross_validation(X, y)
    
    # Demo 5: Model persistence
    demo_model_persistence(predictor)
    
    logger.info("\n" + "="*60)
    logger.info("All demonstrations completed successfully!")
    logger.info("="*60)


if __name__ == "__main__":
    main()

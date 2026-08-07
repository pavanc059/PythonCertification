"""
Unit Tests for TransformerPredictor

Tests the Transformer model implementation for multi-variate market analysis
with attention weight visualization.

Requirements: 13.2
"""

import pytest
import numpy as np
import torch
from stockiq.models.deep.transformer import (
    TransformerPredictor,
    TransformerModel,
    PositionalEncoding,
    Prediction
)


class TestPositionalEncoding:
    """Test PositionalEncoding module"""
    
    def test_positional_encoding_initialization(self):
        """Test that positional encoding initializes correctly"""
        d_model = 128
        max_len = 5000
        pos_enc = PositionalEncoding(d_model=d_model, max_len=max_len)
        
        assert pos_enc.pe.shape == (1, max_len, d_model)
    
    def test_positional_encoding_forward(self):
        """Test positional encoding forward pass"""
        d_model = 128
        batch_size = 4
        seq_length = 60
        
        pos_enc = PositionalEncoding(d_model=d_model)
        x = torch.randn(batch_size, seq_length, d_model)
        
        output = pos_enc(x)
        
        assert output.shape == (batch_size, seq_length, d_model)
    
    def test_positional_encoding_deterministic(self):
        """Test that positional encoding is deterministic"""
        d_model = 64
        pos_enc = PositionalEncoding(d_model=d_model, dropout=0.0)
        
        x = torch.randn(2, 10, d_model)
        
        output1 = pos_enc(x)
        output2 = pos_enc(x)
        
        # With dropout=0, outputs should be identical
        assert torch.allclose(output1, output2)


class TestTransformerModel:
    """Test TransformerModel architecture"""
    
    def test_transformer_model_initialization(self):
        """Test that Transformer model initializes correctly"""
        input_size = 10
        d_model = 64
        nhead = 4
        num_layers = 2
        
        model = TransformerModel(
            input_size=input_size,
            d_model=d_model,
            nhead=nhead,
            num_layers=num_layers
        )
        
        assert model.input_size == input_size
        assert model.d_model == d_model
        assert model.nhead == nhead
        assert model.num_layers == num_layers
    
    def test_transformer_model_forward(self):
        """Test forward pass through Transformer model"""
        batch_size = 8
        seq_length = 60
        input_size = 10
        d_model = 64
        
        model = TransformerModel(input_size=input_size, d_model=d_model, nhead=4, num_layers=2)
        x = torch.randn(batch_size, seq_length, input_size)
        
        output = model(x)
        
        assert output.shape == (batch_size, 1)
    
    def test_transformer_model_attention_extraction(self):
        """Test attention weight extraction"""
        batch_size = 4
        seq_length = 30
        input_size = 5
        num_layers = 2
        
        model = TransformerModel(input_size=input_size, d_model=32, nhead=4, num_layers=num_layers)
        x = torch.randn(batch_size, seq_length, input_size)
        
        # Forward pass with attention extraction
        output = model(x, return_attention=True)
        attention_weights = model.get_attention_weights()
        
        assert output.shape == (batch_size, 1)
        assert attention_weights is not None
        assert len(attention_weights) == num_layers
        assert attention_weights[0].shape[1] == seq_length  # Attention matrix is (batch, seq, seq)
    
    def test_transformer_model_d_model_divisible_by_nhead(self):
        """Test that d_model must be divisible by nhead"""
        with pytest.raises((AssertionError, RuntimeError)):
            # d_model=65 is not divisible by nhead=4
            # This should fail either in initialization or forward pass
            model = TransformerModel(input_size=10, d_model=65, nhead=4)


class TestPredictionDataclass:
    """Test Prediction dataclass"""
    
    def test_prediction_creation(self):
        """Test creating valid prediction"""
        from datetime import datetime
        
        prediction = Prediction(
            ticker="AAPL",
            timestamp=datetime.now(),
            prediction_type="return",
            value=0.05,
            confidence=85.0,
            lower_bound=0.03,
            upper_bound=0.07,
            model_name="Transformer"
        )
        
        assert prediction.ticker == "AAPL"
        assert prediction.value == 0.05
        assert prediction.confidence == 85.0
        assert prediction.lower_bound == 0.03
        assert prediction.upper_bound == 0.07
    
    def test_prediction_confidence_validation(self):
        """Test that confidence must be in [0, 100]"""
        from datetime import datetime
        
        with pytest.raises(ValueError):
            Prediction(
                ticker="AAPL",
                timestamp=datetime.now(),
                prediction_type="return",
                value=0.05,
                confidence=150.0,  # Invalid: > 100
                lower_bound=0.03,
                upper_bound=0.07
            )
    
    def test_prediction_bounds_validation(self):
        """Test that lower_bound <= upper_bound"""
        from datetime import datetime
        
        with pytest.raises(ValueError):
            Prediction(
                ticker="AAPL",
                timestamp=datetime.now(),
                prediction_type="return",
                value=0.05,
                confidence=85.0,
                lower_bound=0.07,  # Invalid: > upper_bound
                upper_bound=0.03
            )


class TestTransformerPredictor:
    """Test TransformerPredictor interface"""
    
    @pytest.fixture
    def synthetic_data(self):
        """Create synthetic time-series data for testing"""
        np.random.seed(42)
        torch.manual_seed(42)
        
        num_samples = 100
        sequence_length = 30
        num_features = 5
        
        X = np.random.randn(num_samples, sequence_length, num_features).astype(np.float32)
        y = np.random.randn(num_samples).astype(np.float32)
        
        split_idx = int(0.8 * num_samples)
        
        return {
            'X_train': X[:split_idx],
            'y_train': y[:split_idx],
            'X_test': X[split_idx:],
            'y_test': y[split_idx:],
            'num_features': num_features
        }
    
    def test_predictor_initialization(self, synthetic_data):
        """Test TransformerPredictor initialization"""
        predictor = TransformerPredictor(
            input_size=synthetic_data['num_features'],
            d_model=32,
            nhead=4,
            num_layers=2,
            dropout=0.1,
            learning_rate=0.001
        )
        
        assert predictor.input_size == synthetic_data['num_features']
        assert predictor.d_model == 32
        assert predictor.nhead == 4
        assert predictor.num_layers == 2
        assert predictor.dropout == 0.1
        assert predictor.learning_rate == 0.001
    
    def test_predictor_training(self, synthetic_data):
        """Test training the Transformer model"""
        predictor = TransformerPredictor(
            input_size=synthetic_data['num_features'],
            d_model=32,
            nhead=4,
            num_layers=2
        )
        
        history = predictor.train(
            synthetic_data['X_train'],
            synthetic_data['y_train'],
            synthetic_data['X_test'],
            synthetic_data['y_test'],
            epochs=5,
            batch_size=16,
            verbose=False
        )
        
        assert 'train_loss' in history
        assert 'val_loss' in history
        assert 'learning_rates' in history
        assert len(history['train_loss']) > 0
        assert len(history['val_loss']) > 0
    
    def test_predictor_prediction(self, synthetic_data):
        """Test making predictions"""
        predictor = TransformerPredictor(
            input_size=synthetic_data['num_features'],
            d_model=32,
            nhead=4,
            num_layers=2
        )
        
        # Quick training
        predictor.train(
            synthetic_data['X_train'],
            synthetic_data['y_train'],
            epochs=3,
            batch_size=16,
            verbose=False
        )
        
        # Make prediction
        test_sequence = synthetic_data['X_test'][0:1]
        prediction = predictor.predict(
            test_sequence,
            n_iterations=20,
            ticker="TEST",
            prediction_type="return"
        )
        
        assert isinstance(prediction, Prediction)
        assert prediction.ticker == "TEST"
        assert prediction.prediction_type == "return"
        assert 0 <= prediction.confidence <= 100
        assert prediction.lower_bound <= prediction.upper_bound
    
    def test_predictor_prediction_with_attention(self, synthetic_data):
        """Test predictions with attention weight extraction"""
        predictor = TransformerPredictor(
            input_size=synthetic_data['num_features'],
            d_model=32,
            nhead=4,
            num_layers=2
        )
        
        # Quick training
        predictor.train(
            synthetic_data['X_train'],
            synthetic_data['y_train'],
            epochs=3,
            batch_size=16,
            verbose=False
        )
        
        # Make prediction with attention
        test_sequence = synthetic_data['X_test'][0:1]
        prediction = predictor.predict(
            test_sequence,
            n_iterations=20,
            ticker="TEST",
            return_attention=True
        )
        
        assert 'attention_weights' in prediction.metadata
        assert 'num_layers' in prediction.metadata
        assert prediction.metadata['num_layers'] == 2
        assert len(prediction.metadata['attention_weights']) == 2
    
    def test_predictor_uncertainty_quantification(self, synthetic_data):
        """Test uncertainty quantification with MC Dropout"""
        predictor = TransformerPredictor(
            input_size=synthetic_data['num_features'],
            d_model=32,
            nhead=4,
            num_layers=2,
            dropout=0.2  # Higher dropout for uncertainty estimation
        )
        
        # Quick training
        predictor.train(
            synthetic_data['X_train'],
            synthetic_data['y_train'],
            epochs=3,
            batch_size=16,
            verbose=False
        )
        
        # Make prediction with multiple MC iterations
        test_sequence = synthetic_data['X_test'][0:1]
        prediction = predictor.predict(
            test_sequence,
            n_iterations=50,
            ticker="TEST"
        )
        
        # Check uncertainty metrics
        assert 'std_deviation' in prediction.metadata
        assert 'coefficient_variation' in prediction.metadata
        assert prediction.metadata['mc_iterations'] == 50
        assert prediction.metadata['std_deviation'] >= 0
    
    def test_predictor_cross_validation(self, synthetic_data):
        """Test time-series cross-validation"""
        predictor = TransformerPredictor(
            input_size=synthetic_data['num_features'],
            d_model=32,
            nhead=4,
            num_layers=2
        )
        
        cv_results = predictor.cross_validate(
            synthetic_data['X_train'],
            synthetic_data['y_train'],
            n_splits=3,
            epochs=3,
            batch_size=16,
            verbose=False
        )
        
        assert 'fold_losses' in cv_results
        assert 'fold_accuracies' in cv_results
        assert 'mean_loss' in cv_results
        assert 'std_loss' in cv_results
        assert 'mean_accuracy' in cv_results
        assert len(cv_results['fold_losses']) > 0
        assert len(cv_results['fold_accuracies']) > 0
    
    def test_predictor_save_load(self, synthetic_data, tmp_path):
        """Test model saving and loading"""
        predictor = TransformerPredictor(
            input_size=synthetic_data['num_features'],
            d_model=32,
            nhead=4,
            num_layers=2
        )
        
        # Train model
        predictor.train(
            synthetic_data['X_train'],
            synthetic_data['y_train'],
            epochs=3,
            batch_size=16,
            verbose=False
        )
        
        # Make prediction before saving
        test_sequence = synthetic_data['X_test'][0:1]
        prediction_before = predictor.predict(test_sequence, n_iterations=10, ticker="TEST")
        
        # Save model
        model_path = tmp_path / "transformer_model.pth"
        predictor.save_model(str(model_path))
        
        # Create new predictor and load model
        predictor_loaded = TransformerPredictor(
            input_size=synthetic_data['num_features'],
            d_model=32,
            nhead=4,
            num_layers=2
        )
        predictor_loaded.load_model(str(model_path))
        
        # Make prediction after loading
        prediction_after = predictor_loaded.predict(test_sequence, n_iterations=10, ticker="TEST")
        
        # Predictions should be similar (allowing for MC Dropout variance)
        assert abs(prediction_before.value - prediction_after.value) < 0.5
    
    def test_predictor_device_detection(self):
        """Test automatic device detection"""
        predictor = TransformerPredictor(input_size=10)
        
        # Should detect CPU or CUDA
        assert predictor.device.type in ['cpu', 'cuda']
    
    def test_predictor_early_stopping(self, synthetic_data):
        """Test early stopping during training"""
        predictor = TransformerPredictor(
            input_size=synthetic_data['num_features'],
            d_model=32,
            nhead=4,
            num_layers=2
        )
        
        history = predictor.train(
            synthetic_data['X_train'],
            synthetic_data['y_train'],
            synthetic_data['X_test'],
            synthetic_data['y_test'],
            epochs=100,  # Large number
            batch_size=16,
            early_stopping_patience=3,
            verbose=False
        )
        
        # Should stop before 100 epochs
        assert len(history['train_loss']) < 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

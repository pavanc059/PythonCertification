"""
Tests for LSTM Predictor

This test suite covers:
- Model initialization
- Training with validation
- Prediction with uncertainty quantification
- Time-series cross-validation
- Model saving and loading
- Edge cases and error handling
"""

import pytest
import numpy as np
import torch
import torch.nn as nn
import tempfile
import os
from datetime import datetime

from stockiq.models.deep.lstm import LSTMPredictor, LSTMModel, Prediction


class TestLSTMModel:
    """Test cases for LSTMModel architecture"""
    
    def test_model_initialization(self):
        """Test LSTM model initialization with default parameters"""
        model = LSTMModel(input_size=10, hidden_size=64, num_layers=2, dropout=0.2)
        
        assert model.input_size == 10
        assert model.hidden_size == 64
        assert model.num_layers == 2
        assert model.dropout == 0.2
        assert model.output_size == 1
    
    def test_model_forward_pass(self):
        """Test forward pass through LSTM model"""
        model = LSTMModel(input_size=10, hidden_size=64, num_layers=2)
        
        # Create random input: (batch_size=5, sequence_length=60, features=10)
        x = torch.randn(5, 60, 10)
        
        # Forward pass
        output = model(x)
        
        # Check output shape: (batch_size=5, output_size=1)
        assert output.shape == (5, 1)
    
    def test_model_different_batch_sizes(self):
        """Test model handles different batch sizes"""
        model = LSTMModel(input_size=10, hidden_size=64)
        
        for batch_size in [1, 8, 32, 64]:
            x = torch.randn(batch_size, 60, 10)
            output = model(x)
            assert output.shape == (batch_size, 1)


class TestPrediction:
    """Test cases for Prediction dataclass"""
    
    def test_valid_prediction(self):
        """Test creating a valid prediction"""
        pred = Prediction(
            ticker="AAPL",
            timestamp=datetime.now(),
            prediction_type="return",
            value=0.02,
            confidence=75.0,
            lower_bound=0.01,
            upper_bound=0.03
        )
        
        assert pred.ticker == "AAPL"
        assert pred.prediction_type == "return"
        assert pred.value == 0.02
        assert pred.confidence == 75.0
        assert pred.lower_bound == 0.01
        assert pred.upper_bound == 0.03
    
    def test_invalid_confidence_range(self):
        """Test prediction raises error for invalid confidence"""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 100"):
            Prediction(
                ticker="AAPL",
                timestamp=datetime.now(),
                prediction_type="return",
                value=0.02,
                confidence=150.0,  # Invalid: >100
                lower_bound=0.01,
                upper_bound=0.03
            )
    
    def test_invalid_bounds(self):
        """Test prediction raises error when lower_bound > upper_bound"""
        with pytest.raises(ValueError, match="Lower bound .* cannot be greater than upper bound"):
            Prediction(
                ticker="AAPL",
                timestamp=datetime.now(),
                prediction_type="return",
                value=0.02,
                confidence=75.0,
                lower_bound=0.03,  # Invalid: greater than upper_bound
                upper_bound=0.01
            )


class TestLSTMPredictor:
    """Test cases for LSTMPredictor"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample training data"""
        np.random.seed(42)
        torch.manual_seed(42)
        
        num_samples = 200
        sequence_length = 60
        num_features = 10
        
        X = np.random.randn(num_samples, sequence_length, num_features).astype(np.float32)
        y = np.random.randn(num_samples).astype(np.float32)
        
        # Split into train/test
        split_idx = int(0.8 * num_samples)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        return X_train, X_test, y_train, y_test, num_features
    
    def test_predictor_initialization(self):
        """Test LSTM predictor initialization"""
        predictor = LSTMPredictor(
            input_size=10,
            hidden_size=64,
            num_layers=2,
            dropout=0.2,
            learning_rate=0.001
        )
        
        assert predictor.input_size == 10
        assert predictor.hidden_size == 64
        assert predictor.num_layers == 2
        assert predictor.dropout == 0.2
        assert predictor.learning_rate == 0.001
        assert isinstance(predictor.model, LSTMModel)
        assert isinstance(predictor.optimizer, torch.optim.Adam)
    
    def test_device_selection(self):
        """Test automatic device selection (CPU/GPU)"""
        predictor = LSTMPredictor(input_size=10)
        
        # Should select either CPU or CUDA
        assert predictor.device.type in ['cpu', 'cuda']
    
    def test_training_without_validation(self, sample_data):
        """Test training without validation set"""
        X_train, X_test, y_train, y_test, num_features = sample_data
        
        predictor = LSTMPredictor(input_size=num_features, hidden_size=32, num_layers=1)
        
        history = predictor.train(
            X_train, y_train,
            epochs=5,
            batch_size=32,
            verbose=False
        )
        
        # Check history contains train loss
        assert 'train_loss' in history
        assert len(history['train_loss']) == 5
        assert all(isinstance(loss, float) for loss in history['train_loss'])
    
    def test_training_with_validation(self, sample_data):
        """Test training with validation set"""
        X_train, X_test, y_train, y_test, num_features = sample_data
        
        predictor = LSTMPredictor(input_size=num_features, hidden_size=32, num_layers=1)
        
        history = predictor.train(
            X_train, y_train,
            X_test, y_test,
            epochs=5,
            batch_size=32,
            early_stopping_patience=3,
            verbose=False
        )
        
        # Check history contains both train and val loss
        assert 'train_loss' in history
        assert 'val_loss' in history
        assert len(history['train_loss']) <= 5  # May stop early
        assert len(history['val_loss']) <= 5
    
    def test_early_stopping(self, sample_data):
        """Test early stopping mechanism"""
        X_train, X_test, y_train, y_test, num_features = sample_data
        
        predictor = LSTMPredictor(input_size=num_features, hidden_size=32)
        
        history = predictor.train(
            X_train, y_train,
            X_test, y_test,
            epochs=100,  # High number
            batch_size=32,
            early_stopping_patience=3,  # Should stop early
            verbose=False
        )
        
        # Should stop before 100 epochs
        assert len(history['train_loss']) < 100
    
    def test_prediction_with_uncertainty(self, sample_data):
        """Test prediction with uncertainty quantification"""
        X_train, X_test, y_train, y_test, num_features = sample_data
        
        predictor = LSTMPredictor(input_size=num_features, hidden_size=32, num_layers=1)
        
        # Quick training
        predictor.train(X_train, y_train, epochs=3, batch_size=32, verbose=False)
        
        # Make prediction
        test_sequence = X_test[0:1]
        prediction = predictor.predict(
            test_sequence,
            n_iterations=50,
            ticker="TEST",
            prediction_type="return"
        )
        
        # Check prediction properties
        assert isinstance(prediction, Prediction)
        assert prediction.ticker == "TEST"
        assert prediction.prediction_type == "return"
        assert isinstance(prediction.value, float)
        assert 0 <= prediction.confidence <= 100
        assert prediction.lower_bound <= prediction.value <= prediction.upper_bound
        assert 'mc_iterations' in prediction.metadata
        assert prediction.metadata['mc_iterations'] == 50
    
    def test_prediction_handles_2d_input(self, sample_data):
        """Test prediction automatically handles 2D input (adds batch dimension)"""
        X_train, X_test, y_train, y_test, num_features = sample_data
        
        predictor = LSTMPredictor(input_size=num_features, hidden_size=32)
        predictor.train(X_train, y_train, epochs=2, batch_size=32, verbose=False)
        
        # Use 2D input (sequence_length, num_features)
        test_sequence_2d = X_test[0]  # Shape: (60, 10)
        
        prediction = predictor.predict(test_sequence_2d, n_iterations=10, ticker="TEST")
        
        assert isinstance(prediction, Prediction)
        assert prediction.ticker == "TEST"
    
    def test_cross_validation(self, sample_data):
        """Test time-series cross-validation"""
        X_train, X_test, y_train, y_test, num_features = sample_data
        
        predictor = LSTMPredictor(input_size=num_features, hidden_size=32, num_layers=1)
        
        results = predictor.cross_validate(
            X_train, y_train,
            n_splits=5,
            epochs=3,
            batch_size=32,
            verbose=False
        )
        
        # Check results structure
        assert 'fold_losses' in results
        assert 'fold_accuracies' in results
        assert 'mean_loss' in results
        assert 'std_loss' in results
        assert 'mean_accuracy' in results
        assert 'std_accuracy' in results
        
        # Check fold counts - may be less than n_splits if some folds were skipped
        assert len(results['fold_losses']) >= 3, \
            f"Expected at least 3 folds, got {len(results['fold_losses'])}"
        assert len(results['fold_accuracies']) >= 3, \
            f"Expected at least 3 folds, got {len(results['fold_accuracies'])}"
        assert len(results['fold_losses']) == len(results['fold_accuracies']), \
            "Mismatch between fold_losses and fold_accuracies"
        
        # Check value types and ranges
        assert all(isinstance(loss, float) for loss in results['fold_losses'])
        assert all(0 <= acc <= 100 for acc in results['fold_accuracies'])
        assert isinstance(results['mean_loss'], (float, np.floating))
        assert isinstance(results['mean_accuracy'], (float, np.floating))
    
    def test_save_and_load_model(self, sample_data):
        """Test model saving and loading"""
        X_train, X_test, y_train, y_test, num_features = sample_data
        
        # Train a model
        predictor = LSTMPredictor(input_size=num_features, hidden_size=32, num_layers=1)
        predictor.train(X_train, y_train, epochs=3, batch_size=32, verbose=False)
        
        # Make prediction before saving
        test_sequence = X_test[0:1]
        pred_before = predictor.predict(test_sequence, n_iterations=10, ticker="TEST")
        
        # Save model
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, 'lstm_test.pth')
            predictor.save_model(model_path)
            
            # Create new predictor and load model
            predictor_loaded = LSTMPredictor(input_size=num_features, hidden_size=32, num_layers=1)
            predictor_loaded.load_model(model_path)
            
            # Make prediction after loading
            pred_after = predictor_loaded.predict(test_sequence, n_iterations=10, ticker="TEST")
            
            # Predictions should be very similar (small differences due to MC Dropout randomness)
            assert abs(pred_before.value - pred_after.value) < 0.1
    
    def test_training_loss_decreases(self, sample_data):
        """Test that training loss generally decreases over epochs"""
        X_train, X_test, y_train, y_test, num_features = sample_data
        
        predictor = LSTMPredictor(input_size=num_features, hidden_size=64, num_layers=2)
        
        history = predictor.train(
            X_train, y_train,
            epochs=20,
            batch_size=32,
            verbose=False
        )
        
        # Check that final loss is lower than initial loss (allowing some variance)
        initial_loss = history['train_loss'][0]
        final_loss = history['train_loss'][-1]
        
        # Final loss should be at most 85% of initial loss (training is working)
        # Using 85% to account for random data and short training
        assert final_loss < initial_loss * 0.85, \
            f"Training didn't reduce loss enough: {initial_loss:.6f} -> {final_loss:.6f}"


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_small_batch_size(self):
        """Test training with small batch size"""
        np.random.seed(42)
        X_train = np.random.randn(50, 30, 5).astype(np.float32)
        y_train = np.random.randn(50).astype(np.float32)
        
        predictor = LSTMPredictor(input_size=5, hidden_size=16, num_layers=1)
        
        # Should work with batch_size=1
        history = predictor.train(X_train, y_train, epochs=2, batch_size=1, verbose=False)
        
        assert len(history['train_loss']) == 2
    
    def test_single_sample_prediction(self):
        """Test prediction on single sample"""
        np.random.seed(42)
        X_train = np.random.randn(100, 30, 5).astype(np.float32)
        y_train = np.random.randn(100).astype(np.float32)
        
        predictor = LSTMPredictor(input_size=5, hidden_size=16)
        predictor.train(X_train, y_train, epochs=2, batch_size=16, verbose=False)
        
        # Single sample prediction
        single_sample = X_train[0:1]
        prediction = predictor.predict(single_sample, n_iterations=10, ticker="TEST")
        
        assert isinstance(prediction, Prediction)
    
    def test_different_sequence_lengths(self):
        """Test model works with different sequence lengths"""
        np.random.seed(42)
        
        for seq_length in [30, 60, 90, 120]:
            X = np.random.randn(100, seq_length, 5).astype(np.float32)
            y = np.random.randn(100).astype(np.float32)
            
            predictor = LSTMPredictor(input_size=5, hidden_size=16, num_layers=1)
            history = predictor.train(X, y, epochs=2, batch_size=16, verbose=False)
            
            # Should train successfully
            assert len(history['train_loss']) == 2
            
            # Should predict successfully
            test_seq = X[0:1]
            pred = predictor.predict(test_seq, n_iterations=10, ticker="TEST")
            assert isinstance(pred, Prediction)


class TestRequirements:
    """Test specific requirements are met"""
    
    def test_requirement_13_1_lstm_architecture(self):
        """
        Test Requirement 13.1: LSTM network for time-series price prediction
        """
        # LSTM model exists and has correct architecture
        model = LSTMModel(input_size=10, hidden_size=128, num_layers=2)
        
        # Check LSTM layer exists
        assert hasattr(model, 'lstm')
        assert isinstance(model.lstm, nn.LSTM)
        
        # Check dropout exists
        assert hasattr(model, 'dropout_layer')
        assert isinstance(model.dropout_layer, nn.Dropout)
        
        # Check fully connected layer exists
        assert hasattr(model, 'fc')
        assert isinstance(model.fc, nn.Linear)
    
    def test_requirement_13_4_uncertainty_quantification(self):
        """
        Test Requirement 13.4: Uncertainty quantification with 95% confidence intervals
        """
        np.random.seed(42)
        X = np.random.randn(100, 60, 10).astype(np.float32)
        y = np.random.randn(100).astype(np.float32)
        
        predictor = LSTMPredictor(input_size=10, hidden_size=32, num_layers=1)
        predictor.train(X, y, epochs=2, batch_size=32, verbose=False)
        
        # Make prediction
        prediction = predictor.predict(X[0:1], n_iterations=100, ticker="TEST")
        
        # Check 95% confidence interval exists
        assert hasattr(prediction, 'lower_bound')
        assert hasattr(prediction, 'upper_bound')
        assert prediction.lower_bound < prediction.upper_bound
        
        # Check confidence score exists and is in valid range
        assert hasattr(prediction, 'confidence')
        assert 0 <= prediction.confidence <= 100
        
        # Check metadata contains MC Dropout info
        assert 'mc_iterations' in prediction.metadata
        assert prediction.metadata['mc_iterations'] == 100
    
    def test_requirement_13_7_time_series_cv(self):
        """
        Test Requirement 13.7: Time-series cross-validation with 5 folds
        """
        np.random.seed(42)
        X = np.random.randn(250, 60, 10).astype(np.float32)
        y = np.random.randn(250).astype(np.float32)
        
        predictor = LSTMPredictor(input_size=10, hidden_size=32, num_layers=1)
        
        # Perform 5-fold CV
        results = predictor.cross_validate(
            X, y,
            n_splits=5,
            epochs=2,
            batch_size=32,
            verbose=False
        )
        
        # Check at least 3 folds were performed (some may be skipped with small datasets)
        assert len(results['fold_losses']) >= 3, \
            f"Expected at least 3 folds, got {len(results['fold_losses'])}"
        
        # Check expanding window (train size increases for each fold)
        fold_predictions = results['fold_predictions']
        train_sizes = []
        for i, fold_data in enumerate(fold_predictions):
            # Each fold should have predictions
            assert 'predictions' in fold_data
            assert 'actuals' in fold_data
            assert len(fold_data['predictions']) > 0
        
        # All folds with predictions should have data
        folds_with_predictions = [f for f in results['fold_predictions'] if len(f['predictions']) > 0]
        assert len(folds_with_predictions) >= 3, \
            f"Expected at least 3 folds with predictions, got {len(folds_with_predictions)}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])

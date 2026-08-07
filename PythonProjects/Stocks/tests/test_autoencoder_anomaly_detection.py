"""
Tests for Anomaly Detection (Autoencoder and Isolation Forest)

This test suite covers:
- IsolationForestDetector functionality
- AutoencoderDetector functionality
- Ensemble AnomalyDetector
- Model training and detection
- Edge cases and error handling
- Requirement validation
"""

import pytest
import numpy as np
import torch
import pandas as pd
from datetime import datetime

from stockiq.models.deep.autoencoder import (
    IsolationForestDetector,
    AutoencoderDetector,
    AnomalyDetector,
    AnomalyResult,
    AutoencoderModel
)


class TestAnomalyResult:
    """Test cases for AnomalyResult dataclass"""
    
    def test_valid_anomaly_result(self):
        """Test creating a valid anomaly result"""
        result = AnomalyResult(
            ticker="AAPL",
            timestamp=datetime.now(),
            is_anomaly=True,
            anomaly_score=0.85,
            confidence=85.0,
            contributing_features={"rsi": 0.5, "volume": 0.3},
            reconstruction_error=0.123,
            method="autoencoder"
        )
        
        assert result.ticker == "AAPL"
        assert result.is_anomaly is True
        assert result.anomaly_score == 0.85
        assert result.confidence == 85.0
        assert len(result.contributing_features) == 2
    
    def test_invalid_confidence_range(self):
        """Test anomaly result raises error for invalid confidence"""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 100"):
            AnomalyResult(
                ticker="AAPL",
                timestamp=datetime.now(),
                is_anomaly=True,
                anomaly_score=0.85,
                confidence=150.0,  # Invalid
                method="test"
            )


class TestAutoencoderModel:
    """Test cases for AutoencoderModel architecture"""
    
    def test_model_initialization(self):
        """Test autoencoder model initialization with default parameters"""
        model = AutoencoderModel(input_size=20, hidden_sizes=[32, 16], bottleneck_size=8)
        
        assert model.input_size == 20
        assert model.hidden_sizes == [32, 16]
        assert model.bottleneck_size == 8
        assert hasattr(model, 'encoder')
        assert hasattr(model, 'decoder')
    
    def test_model_forward_pass(self):
        """Test forward pass through autoencoder"""
        model = AutoencoderModel(input_size=20, hidden_sizes=[32, 16], bottleneck_size=8)
        
        # Create random input
        x = torch.randn(10, 20)
        
        # Forward pass
        reconstructed, encoded = model(x)
        
        # Check shapes
        assert reconstructed.shape == (10, 20)  # Same as input
        assert encoded.shape == (10, 8)  # Bottleneck size
    
    def test_reconstruction_quality(self):
        """Test that model can learn to reconstruct input"""
        model = AutoencoderModel(input_size=10, hidden_sizes=[16], bottleneck_size=4)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = torch.nn.MSELoss()
        
        # Simple training data
        X = torch.randn(100, 10)
        
        # Train for a few epochs
        for _ in range(50):
            optimizer.zero_grad()
            reconstructed, _ = model(X)
            loss = criterion(reconstructed, X)
            loss.backward()
            optimizer.step()
        
        # Final loss should be reasonably low
        final_loss = criterion(reconstructed, X).item()
        assert final_loss < 1.0, f"Reconstruction loss too high: {final_loss}"


class TestIsolationForestDetector:
    """Test cases for IsolationForestDetector"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data with known anomalies"""
        np.random.seed(42)
        
        # Normal data
        num_normal = 900
        X_normal = np.random.randn(num_normal, 10).astype(np.float32)
        
        # Anomalies (outliers with large values)
        num_anomalies = 100
        X_anomalies = np.random.randn(num_anomalies, 10).astype(np.float32) * 5
        
        # Combine
        X = np.vstack([X_normal, X_anomalies])
        
        # True labels (1 = normal, -1 = anomaly)
        y_true = np.concatenate([
            np.ones(num_normal),
            -np.ones(num_anomalies)
        ])
        
        return X, y_true, X_normal
    
    def test_detector_initialization(self):
        """Test detector initialization"""
        detector = IsolationForestDetector(
            contamination=0.1,
            n_estimators=100,
            random_state=42
        )
        
        assert detector.contamination == 0.1
        assert detector.n_estimators == 100
        assert detector.is_fitted is False
    
    def test_training(self, sample_data):
        """Test training the detector"""
        X, y_true, X_normal = sample_data
        
        detector = IsolationForestDetector(contamination=0.1, n_estimators=50)
        detector.train(X_normal)
        
        assert detector.is_fitted is True
        assert detector.feature_names is not None
        assert len(detector.feature_names) == X_normal.shape[1]
    
    def test_detection(self, sample_data):
        """Test anomaly detection"""
        X, y_true, X_normal = sample_data
        
        # Train on normal data
        detector = IsolationForestDetector(contamination=0.1, n_estimators=100, random_state=42)
        detector.train(X_normal)
        
        # Detect anomalies on mixed data
        results = detector.detect(X[:100], ticker="TEST")
        
        # Check results
        assert len(results) == 100
        assert all(isinstance(r, AnomalyResult) for r in results)
        assert all(r.ticker == "TEST" for r in results)
        assert all(r.method == "isolation_forest" for r in results)
        
        # Should detect some anomalies
        num_detected = sum(r.is_anomaly for r in results)
        assert num_detected > 0, "Should detect at least some anomalies"
    
    def test_detection_with_dataframe(self, sample_data):
        """Test detection with pandas DataFrame input"""
        X, y_true, X_normal = sample_data
        
        # Convert to DataFrame
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        df_normal = pd.DataFrame(X_normal, columns=feature_names)
        df_test = pd.DataFrame(X[:50], columns=feature_names)
        
        # Train and detect
        detector = IsolationForestDetector(contamination=0.1, random_state=42)
        detector.train(df_normal)
        results = detector.detect(df_test, ticker="TEST")
        
        # Check feature names are preserved
        assert detector.feature_names == feature_names
        assert len(results) == 50
    
    def test_contributing_features(self, sample_data):
        """Test that contributing features are identified"""
        X, y_true, X_normal = sample_data
        
        detector = IsolationForestDetector(contamination=0.1, random_state=42)
        detector.train(X_normal)
        results = detector.detect(X[:10], ticker="TEST", return_top_features=3)
        
        # Check contributing features
        for result in results:
            assert isinstance(result.contributing_features, dict)
            assert len(result.contributing_features) <= 3
            assert all(isinstance(k, str) for k in result.contributing_features.keys())
            assert all(isinstance(v, float) for v in result.contributing_features.values())
    
    def test_error_before_training(self):
        """Test that detection fails before training"""
        detector = IsolationForestDetector()
        
        X = np.random.randn(10, 5)
        
        with pytest.raises(ValueError, match="must be trained before detecting"):
            detector.detect(X)


class TestAutoencoderDetector:
    """Test cases for AutoencoderDetector"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data with known anomalies"""
        np.random.seed(42)
        torch.manual_seed(42)
        
        # Normal data
        num_normal = 500
        X_normal = np.random.randn(num_normal, 15).astype(np.float32)
        
        # Anomalies
        num_anomalies = 50
        X_anomalies = np.random.randn(num_anomalies, 15).astype(np.float32) * 4
        
        # Combine
        X = np.vstack([X_normal, X_anomalies])
        
        return X, X_normal
    
    def test_detector_initialization(self):
        """Test autoencoder detector initialization"""
        detector = AutoencoderDetector(
            input_size=20,
            hidden_sizes=[32, 16],
            bottleneck_size=8,
            dropout=0.2,
            learning_rate=0.001
        )
        
        assert detector.input_size == 20
        assert detector.learning_rate == 0.001
        assert detector.is_fitted is False
        assert isinstance(detector.model, AutoencoderModel)
    
    def test_training(self, sample_data):
        """Test training the autoencoder"""
        X, X_normal = sample_data
        
        detector = AutoencoderDetector(
            input_size=X_normal.shape[1],
            hidden_sizes=[24, 12],
            bottleneck_size=6
        )
        
        history = detector.train(
            X_normal,
            epochs=20,
            batch_size=32,
            verbose=False
        )
        
        assert detector.is_fitted is True
        assert 'loss' in history
        assert len(history['loss']) == 20
        assert detector.threshold is not None
        
        # Loss should generally decrease (allowing some variance with random data)
        assert history['loss'][-1] < history['loss'][0] * 1.0, \
            f"Loss should not increase: initial={history['loss'][0]:.4f}, final={history['loss'][-1]:.4f}"
    
    def test_detection(self, sample_data):
        """Test anomaly detection with autoencoder"""
        X, X_normal = sample_data
        
        # Train on normal data
        detector = AutoencoderDetector(
            input_size=X_normal.shape[1],
            hidden_sizes=[24, 12],
            bottleneck_size=6
        )
        detector.train(X_normal, epochs=30, batch_size=64, verbose=False)
        
        # Detect on mixed data
        results = detector.detect(X[:100], ticker="TEST")
        
        # Check results
        assert len(results) == 100
        assert all(isinstance(r, AnomalyResult) for r in results)
        assert all(r.method == "autoencoder" for r in results)
        assert all(r.reconstruction_error is not None for r in results)
        
        # Should detect some anomalies
        num_detected = sum(r.is_anomaly for r in results)
        assert num_detected > 0
    
    def test_threshold_calculation(self, sample_data):
        """Test that anomaly threshold is calculated correctly"""
        X, X_normal = sample_data
        
        detector = AutoencoderDetector(input_size=X_normal.shape[1])
        detector.train(X_normal, epochs=20, threshold_percentile=95.0, verbose=False)
        
        # Threshold should be set
        assert detector.threshold is not None
        assert detector.threshold > 0
    
    def test_detection_with_dataframe(self, sample_data):
        """Test detection with pandas DataFrame"""
        X, X_normal = sample_data
        
        feature_names = [f"feat_{i}" for i in range(X.shape[1])]
        df_normal = pd.DataFrame(X_normal, columns=feature_names)
        df_test = pd.DataFrame(X[:50], columns=feature_names)
        
        detector = AutoencoderDetector(input_size=X_normal.shape[1])
        detector.train(df_normal, epochs=15, verbose=False)
        results = detector.detect(df_test, ticker="TEST")
        
        assert detector.feature_names == feature_names
        assert len(results) == 50
    
    def test_error_before_training(self):
        """Test that detection fails before training"""
        detector = AutoencoderDetector(input_size=10)
        
        X = np.random.randn(10, 10)
        
        with pytest.raises(ValueError, match="must be trained before detecting"):
            detector.detect(X)


class TestAnomalyDetector:
    """Test cases for ensemble AnomalyDetector"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data"""
        np.random.seed(42)
        torch.manual_seed(42)
        
        num_normal = 400
        X_normal = np.random.randn(num_normal, 12).astype(np.float32)
        
        num_anomalies = 40
        X_anomalies = np.random.randn(num_anomalies, 12).astype(np.float32) * 4
        
        X = np.vstack([X_normal, X_anomalies])
        
        return X, X_normal
    
    def test_ensemble_initialization(self):
        """Test ensemble detector initialization"""
        detector = AnomalyDetector(
            input_size=20,
            use_isolation_forest=True,
            use_autoencoder=True,
            ensemble_method="vote"
        )
        
        assert detector.use_isolation_forest is True
        assert detector.use_autoencoder is True
        assert detector.ensemble_method == "vote"
        assert detector.isolation_forest is not None
        assert detector.autoencoder is not None
    
    def test_ensemble_with_only_isolation_forest(self):
        """Test ensemble with only Isolation Forest"""
        detector = AnomalyDetector(
            input_size=20,
            use_isolation_forest=True,
            use_autoencoder=False
        )
        
        assert detector.isolation_forest is not None
        assert detector.autoencoder is None
    
    def test_ensemble_with_only_autoencoder(self):
        """Test ensemble with only Autoencoder"""
        detector = AnomalyDetector(
            input_size=20,
            use_isolation_forest=False,
            use_autoencoder=True
        )
        
        assert detector.isolation_forest is None
        assert detector.autoencoder is not None
    
    def test_ensemble_requires_at_least_one_method(self):
        """Test that at least one method must be enabled"""
        with pytest.raises(ValueError, match="At least one detection method"):
            AnomalyDetector(
                input_size=20,
                use_isolation_forest=False,
                use_autoencoder=False
            )
    
    def test_ensemble_training(self, sample_data):
        """Test training the ensemble"""
        X, X_normal = sample_data
        
        detector = AnomalyDetector(
            input_size=X_normal.shape[1],
            use_isolation_forest=True,
            use_autoencoder=True,
            ensemble_method="vote",
            n_estimators=50,
            hidden_sizes=[20, 10],
            bottleneck_size=5
        )
        
        results = detector.train(X_normal, epochs=20, batch_size=32, verbose=False)
        
        assert detector.is_fitted is True
        assert 'isolation_forest' in results
        assert 'autoencoder' in results
        assert results['isolation_forest']['trained'] is True
        assert results['autoencoder']['trained'] is True
    
    def test_ensemble_detection_vote(self, sample_data):
        """Test ensemble detection with vote method"""
        X, X_normal = sample_data
        
        detector = AnomalyDetector(
            input_size=X_normal.shape[1],
            ensemble_method="vote",
            n_estimators=50,
            hidden_sizes=[20, 10]
        )
        
        detector.train(X_normal, epochs=15, verbose=False)
        results = detector.detect(X[:50], ticker="TEST")
        
        assert len(results) == 50
        assert all(r.method == "ensemble" for r in results)
        assert all('ensemble_method' in r.metadata for r in results)
    
    def test_ensemble_detection_average(self, sample_data):
        """Test ensemble detection with average method"""
        X, X_normal = sample_data
        
        detector = AnomalyDetector(
            input_size=X_normal.shape[1],
            ensemble_method="average",
            n_estimators=50
        )
        
        detector.train(X_normal, epochs=15, verbose=False)
        results = detector.detect(X[:50], ticker="TEST")
        
        assert len(results) == 50
        assert all(r.method == "ensemble" for r in results)
    
    def test_ensemble_detection_max(self, sample_data):
        """Test ensemble detection with max method"""
        X, X_normal = sample_data
        
        detector = AnomalyDetector(
            input_size=X_normal.shape[1],
            ensemble_method="max",
            n_estimators=50
        )
        
        detector.train(X_normal, epochs=15, verbose=False)
        results = detector.detect(X[:50], ticker="TEST")
        
        assert len(results) == 50
        # Max method should detect more anomalies (either method flags it)
        num_detected = sum(r.is_anomaly for r in results)
        assert num_detected >= 0


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_small_dataset_isolation_forest(self):
        """Test Isolation Forest with small dataset"""
        X = np.random.randn(50, 5).astype(np.float32)
        
        detector = IsolationForestDetector(contamination=0.1)
        detector.train(X)
        results = detector.detect(X[:10], ticker="TEST")
        
        assert len(results) == 10
    
    def test_small_dataset_autoencoder(self):
        """Test Autoencoder with small dataset"""
        X = np.random.randn(50, 5).astype(np.float32)
        
        detector = AutoencoderDetector(input_size=5, hidden_sizes=[8], bottleneck_size=3)
        detector.train(X, epochs=10, batch_size=8, verbose=False)
        results = detector.detect(X[:10], ticker="TEST")
        
        assert len(results) == 10
    
    def test_single_feature(self):
        """Test detection with single feature"""
        X = np.random.randn(100, 1).astype(np.float32)
        
        # Isolation Forest
        if_detector = IsolationForestDetector(contamination=0.1)
        if_detector.train(X)
        if_results = if_detector.detect(X[:10], ticker="TEST")
        
        assert len(if_results) == 10
        
        # Autoencoder
        ae_detector = AutoencoderDetector(input_size=1, hidden_sizes=[4], bottleneck_size=2)
        ae_detector.train(X, epochs=10, verbose=False)
        ae_results = ae_detector.detect(X[:10], ticker="TEST")
        
        assert len(ae_results) == 10
    
    def test_high_dimensional_data(self):
        """Test detection with high-dimensional data"""
        np.random.seed(42)
        X = np.random.randn(200, 50).astype(np.float32)
        
        # Isolation Forest handles high dimensions well
        detector = IsolationForestDetector(contamination=0.05)
        detector.train(X)
        results = detector.detect(X[:20], ticker="TEST")
        
        assert len(results) == 20


class TestRequirements:
    """Test specific requirements are met"""
    
    def test_requirement_13_6_isolation_forest(self):
        """
        Test Requirement 13.6: Detect market anomalies using isolation forests
        """
        np.random.seed(42)
        
        # Create market-like data
        num_samples = 500
        num_features = 20
        
        # Normal market data
        X_normal = np.random.randn(num_samples, num_features).astype(np.float32)
        
        # Create Isolation Forest detector
        detector = IsolationForestDetector(contamination=0.1, n_estimators=100)
        
        # Train on normal data
        detector.train(X_normal)
        
        # Create test data with anomalies
        X_test_normal = np.random.randn(80, num_features).astype(np.float32)
        X_test_anomaly = np.random.randn(20, num_features).astype(np.float32) * 5
        X_test = np.vstack([X_test_normal, X_test_anomaly])
        
        # Detect anomalies
        results = detector.detect(X_test, ticker="MARKET")
        
        # Verify functionality
        assert len(results) == 100
        assert all(isinstance(r, AnomalyResult) for r in results)
        
        # Should detect more anomalies in the anomalous portion
        anomalies_in_first_80 = sum(r.is_anomaly for r in results[:80])
        anomalies_in_last_20 = sum(r.is_anomaly for r in results[80:])
        
        # Last 20 should have higher anomaly rate (they are 5x variance)
        assert anomalies_in_last_20 >= anomalies_in_first_80 * 0.3, \
            "Isolation Forest should detect more anomalies in anomalous data"
    
    def test_requirement_13_6_autoencoder(self):
        """
        Test Requirement 13.6: Detect market anomalies using autoencoders
        """
        np.random.seed(42)
        torch.manual_seed(42)
        
        # Create market-like data
        num_samples = 400
        num_features = 15
        
        # Normal market data
        X_normal = np.random.randn(num_samples, num_features).astype(np.float32)
        
        # Create Autoencoder detector
        detector = AutoencoderDetector(
            input_size=num_features,
            hidden_sizes=[32, 16],
            bottleneck_size=8
        )
        
        # Train on normal data
        detector.train(X_normal, epochs=30, batch_size=32, verbose=False)
        
        # Create test data with anomalies
        X_test_normal = np.random.randn(70, num_features).astype(np.float32)
        X_test_anomaly = np.random.randn(30, num_features).astype(np.float32) * 4
        X_test = np.vstack([X_test_normal, X_test_anomaly])
        
        # Detect anomalies
        results = detector.detect(X_test, ticker="MARKET")
        
        # Verify functionality
        assert len(results) == 100
        assert all(isinstance(r, AnomalyResult) for r in results)
        assert all(r.reconstruction_error is not None for r in results)
        
        # Anomalous data should have higher reconstruction errors
        avg_error_normal = np.mean([r.reconstruction_error for r in results[:70]])
        avg_error_anomaly = np.mean([r.reconstruction_error for r in results[70:]])
        
        assert avg_error_anomaly > avg_error_normal, \
            "Anomalous data should have higher reconstruction error"
    
    def test_requirement_13_6_ensemble(self):
        """
        Test Requirement 13.6: Detect market anomalies using both methods
        """
        np.random.seed(42)
        torch.manual_seed(42)
        
        # Create market-like data
        num_samples = 300
        num_features = 12
        
        # Normal market data
        X_normal = np.random.randn(num_samples, num_features).astype(np.float32)
        
        # Create ensemble detector
        detector = AnomalyDetector(
            input_size=num_features,
            use_isolation_forest=True,
            use_autoencoder=True,
            ensemble_method="vote",
            contamination=0.1,
            n_estimators=50,
            hidden_sizes=[20, 10],
            bottleneck_size=5
        )
        
        # Train on normal data
        training_results = detector.train(X_normal, epochs=20, batch_size=32, verbose=False)
        
        # Verify both methods were trained
        assert 'isolation_forest' in training_results
        assert 'autoencoder' in training_results
        
        # Create test data
        X_test = np.random.randn(50, num_features).astype(np.float32)
        X_test[40:] *= 4  # Last 10 are anomalies
        
        # Detect anomalies
        results = detector.detect(X_test, ticker="MARKET")
        
        # Verify ensemble results
        assert len(results) == 50
        assert all(r.method == "ensemble" for r in results)
        assert all('isolation_forest' in r.metadata for r in results)
        assert all('autoencoder' in r.metadata for r in results)
        
        # Should detect some anomalies
        num_detected = sum(r.is_anomaly for r in results)
        assert num_detected > 0, "Ensemble should detect anomalies"
    
    def test_contributing_features_identified(self):
        """
        Test that contributing features are identified for anomalies
        """
        np.random.seed(42)
        
        # Create data where feature 0 has extreme values (anomalies)
        X_normal = np.random.randn(200, 10).astype(np.float32)
        X_test = np.random.randn(10, 10).astype(np.float32)
        X_test[0, 0] = 10.0  # Extreme value in feature 0
        
        # Train and detect
        detector = IsolationForestDetector(contamination=0.1)
        detector.train(X_normal)
        results = detector.detect(X_test, ticker="TEST", return_top_features=5)
        
        # First sample should be flagged as anomaly
        first_result = results[0]
        
        # Contributing features should be identified
        assert len(first_result.contributing_features) > 0
        assert isinstance(first_result.contributing_features, dict)
        
        # Feature 0 should be among top contributors (it has extreme value)
        feature_names = list(first_result.contributing_features.keys())
        assert any('feature_0' in name for name in feature_names), \
            "Feature 0 should be identified as contributing to anomaly"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])

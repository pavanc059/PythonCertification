"""
Unit tests for data preprocessing module.

Tests verify:
- Feature normalization with StandardScaler
- Sequence creation for time-series models
- Train/test splitting with temporal ordering
- Time-series cross-validation without data leakage
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler

from stockiq.models.preprocessing import (
    normalize_features,
    create_sequences,
    split_train_test,
    get_time_series_cv_splitter,
    preprocess_for_training
)


class TestNormalizeFeatures:
    """Tests for normalize_features function"""
    
    def test_normalize_basic(self):
        """Test basic normalization functionality"""
        # Create sample data
        data = pd.DataFrame({
            'feature1': [100, 110, 120, 130, 140],
            'feature2': [1000, 1100, 1200, 1300, 1400]
        })
        
        # Normalize
        normalized = normalize_features(data)
        
        # Check output is DataFrame
        assert isinstance(normalized, pd.DataFrame)
        
        # Check shape is preserved
        assert normalized.shape == data.shape
        
        # Check columns are preserved
        assert list(normalized.columns) == list(data.columns)
        
        # Check index is preserved
        assert list(normalized.index) == list(data.index)
        
        # Check mean is approximately 0
        assert np.abs(normalized.mean().mean()) < 1e-10
        
        # Check std is approximately 1 (with small sample correction)
        # StandardScaler uses ddof=0, pandas .std() uses ddof=1 by default
        # For small samples, there can be a difference
        assert np.abs(normalized.std(ddof=0).mean() - 1.0) < 0.1
    
    def test_normalize_preserves_structure(self):
        """Test that normalization preserves DataFrame structure"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'price': np.random.randn(10) * 100 + 1000,
            'volume': np.random.randn(10) * 10000 + 50000
        }, index=dates)
        
        normalized = normalize_features(data)
        
        # Check DatetimeIndex is preserved
        assert isinstance(normalized.index, pd.DatetimeIndex)
        assert list(normalized.index) == list(data.index)
    
    def test_normalize_empty_dataframe(self):
        """Test normalization with empty DataFrame"""
        data = pd.DataFrame()
        result = normalize_features(data)
        assert result.empty
    
    def test_normalize_single_column(self):
        """Test normalization with single column"""
        data = pd.DataFrame({'feature1': [1, 2, 3, 4, 5]})
        normalized = normalize_features(data)
        assert normalized.shape == (5, 1)
        assert np.abs(normalized['feature1'].mean()) < 1e-10


class TestCreateSequences:
    """Tests for create_sequences function"""
    
    def test_create_sequences_basic(self):
        """Test basic sequence creation"""
        data = pd.DataFrame({
            'feature1': range(100),
            'feature2': range(100, 200)
        })
        
        sequences = create_sequences(data, sequence_length=10)
        
        # Check output is numpy array
        assert isinstance(sequences, np.ndarray)
        
        # Check shape (num_sequences, sequence_length, num_features)
        assert sequences.shape == (91, 10, 2)
        
        # Check first sequence
        assert np.array_equal(sequences[0, :, 0], np.arange(0, 10))
        assert np.array_equal(sequences[0, :, 1], np.arange(100, 110))
        
        # Check second sequence (shifted by 1)
        assert np.array_equal(sequences[1, :, 0], np.arange(1, 11))
        assert np.array_equal(sequences[1, :, 1], np.arange(101, 111))
    
    def test_create_sequences_different_lengths(self):
        """Test sequence creation with different sequence lengths"""
        data = pd.DataFrame({'feature': range(100)})
        
        # Test with sequence_length=60 (common for LSTM)
        sequences_60 = create_sequences(data, sequence_length=60)
        assert sequences_60.shape == (41, 60, 1)
        
        # Test with sequence_length=30
        sequences_30 = create_sequences(data, sequence_length=30)
        assert sequences_30.shape == (71, 30, 1)
    
    def test_create_sequences_temporal_order(self):
        """Test that sequences preserve temporal order"""
        data = pd.DataFrame({'feature': [10, 20, 30, 40, 50]})
        sequences = create_sequences(data, sequence_length=3)
        
        # First sequence should be [10, 20, 30]
        assert np.array_equal(sequences[0, :, 0], np.array([10, 20, 30]))
        
        # Second sequence should be [20, 30, 40]
        assert np.array_equal(sequences[1, :, 0], np.array([20, 30, 40]))
        
        # Third sequence should be [30, 40, 50]
        assert np.array_equal(sequences[2, :, 0], np.array([30, 40, 50]))
    
    def test_create_sequences_invalid_inputs(self):
        """Test error handling for invalid inputs"""
        data = pd.DataFrame({'feature': range(10)})
        
        # Empty DataFrame
        with pytest.raises(ValueError, match="empty DataFrame"):
            create_sequences(pd.DataFrame(), sequence_length=5)
        
        # Sequence length < 1
        with pytest.raises(ValueError, match="must be >= 1"):
            create_sequences(data, sequence_length=0)
        
        # Sequence length >= data length
        with pytest.raises(ValueError, match="must be less than data length"):
            create_sequences(data, sequence_length=10)
        
        with pytest.raises(ValueError, match="must be less than data length"):
            create_sequences(data, sequence_length=11)


class TestSplitTrainTest:
    """Tests for split_train_test function"""
    
    def test_split_train_test_basic(self):
        """Test basic train/test split"""
        X = pd.DataFrame({
            'feature1': range(100),
            'feature2': range(100, 200)
        })
        y = pd.Series(range(200, 300))
        
        X_train, X_test, y_train, y_test = split_train_test(X, y, test_size=0.2)
        
        # Check sizes
        assert len(X_train) == 80
        assert len(X_test) == 20
        assert len(y_train) == 80
        assert len(y_test) == 20
        
        # Check all are DataFrames/Series
        assert isinstance(X_train, pd.DataFrame)
        assert isinstance(X_test, pd.DataFrame)
        assert isinstance(y_train, pd.Series)
        assert isinstance(y_test, pd.Series)
    
    def test_split_temporal_order(self):
        """Test that split preserves temporal order (no data leakage)"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        X = pd.DataFrame({'feature': range(100)}, index=dates)
        y = pd.Series(range(100), index=dates)
        
        X_train, X_test, y_train, y_test = split_train_test(X, y, test_size=0.2)
        
        # Training set should come before test set
        assert X_train.index[-1] < X_test.index[0]
        
        # Test set should contain most recent data
        assert X_test.index[-1] == dates[-1]
        
        # Training set should contain oldest data
        assert X_train.index[0] == dates[0]
        
        # No overlap between train and test
        train_indices = set(X_train.index)
        test_indices = set(X_test.index)
        assert len(train_indices.intersection(test_indices)) == 0
    
    def test_split_different_test_sizes(self):
        """Test split with different test sizes"""
        X = pd.DataFrame({'feature': range(100)})
        y = pd.Series(range(100))
        
        # Test with 10% test size
        X_train, X_test, y_train, y_test = split_train_test(X, y, test_size=0.1)
        assert len(X_train) == 90
        assert len(X_test) == 10
        
        # Test with 30% test size
        X_train, X_test, y_train, y_test = split_train_test(X, y, test_size=0.3)
        assert len(X_train) == 70
        assert len(X_test) == 30
    
    def test_split_preserves_index(self):
        """Test that split preserves index"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        X = pd.DataFrame({'feature': range(100)}, index=dates)
        y = pd.Series(range(100), index=dates)
        
        X_train, X_test, y_train, y_test = split_train_test(X, y, test_size=0.2)
        
        # Check that indices are preserved
        assert isinstance(X_train.index, pd.DatetimeIndex)
        assert isinstance(X_test.index, pd.DatetimeIndex)
        assert isinstance(y_train.index, pd.DatetimeIndex)
        assert isinstance(y_test.index, pd.DatetimeIndex)
    
    def test_split_invalid_inputs(self):
        """Test error handling for invalid inputs"""
        X = pd.DataFrame({'feature': range(100)})
        y = pd.Series(range(100))
        
        # Mismatched lengths
        y_short = pd.Series(range(50))
        with pytest.raises(ValueError, match="same length"):
            split_train_test(X, y_short, test_size=0.2)
        
        # Invalid test_size (> 1)
        with pytest.raises(ValueError, match="between 0 and 1"):
            split_train_test(X, y, test_size=1.5)
        
        # Invalid test_size (< 0)
        with pytest.raises(ValueError, match="between 0 and 1"):
            split_train_test(X, y, test_size=-0.1)
        
        # Invalid test_size (0)
        with pytest.raises(ValueError, match="between 0 and 1"):
            split_train_test(X, y, test_size=0)


class TestTimeSeriesCVSplitter:
    """Tests for get_time_series_cv_splitter function"""
    
    def test_cv_splitter_basic(self):
        """Test basic CV splitter creation"""
        splitter = get_time_series_cv_splitter(n_splits=5)
        
        # Check it's a TimeSeriesSplit object
        from sklearn.model_selection import TimeSeriesSplit
        assert isinstance(splitter, TimeSeriesSplit)
    
    def test_cv_splitter_split_behavior(self):
        """Test that CV splitter creates correct folds"""
        X = pd.DataFrame({'feature': range(100)})
        splitter = get_time_series_cv_splitter(n_splits=5)
        
        folds = list(splitter.split(X))
        
        # Check number of folds
        assert len(folds) == 5
        
        # Check that training set grows with each fold
        prev_train_size = 0
        for train_idx, test_idx in folds:
            assert len(train_idx) > prev_train_size
            prev_train_size = len(train_idx)
        
        # Check no data leakage (train indices < test indices)
        for train_idx, test_idx in folds:
            assert max(train_idx) < min(test_idx)
    
    def test_cv_splitter_no_overlap(self):
        """Test that train and test sets don't overlap in each fold"""
        X = pd.DataFrame({'feature': range(100)})
        splitter = get_time_series_cv_splitter(n_splits=5)
        
        for train_idx, test_idx in splitter.split(X):
            train_set = set(train_idx)
            test_set = set(test_idx)
            
            # No overlap
            assert len(train_set.intersection(test_set)) == 0
            
            # All indices are covered
            assert len(train_set) + len(test_set) <= len(X)
    
    def test_cv_splitter_different_n_splits(self):
        """Test CV splitter with different number of splits"""
        X = pd.DataFrame({'feature': range(100)})
        
        # Test with 3 splits
        splitter_3 = get_time_series_cv_splitter(n_splits=3)
        folds_3 = list(splitter_3.split(X))
        assert len(folds_3) == 3
        
        # Test with 10 splits
        splitter_10 = get_time_series_cv_splitter(n_splits=10)
        folds_10 = list(splitter_10.split(X))
        assert len(folds_10) == 10
    
    def test_cv_splitter_invalid_inputs(self):
        """Test error handling for invalid inputs"""
        # n_splits < 2
        with pytest.raises(ValueError, match="must be >= 2"):
            get_time_series_cv_splitter(n_splits=1)


class TestPreprocessForTraining:
    """Tests for complete preprocessing pipeline"""
    
    def test_pipeline_basic(self):
        """Test basic preprocessing pipeline"""
        X = pd.DataFrame({
            'feature1': range(100),
            'feature2': range(100, 200)
        })
        y = pd.Series(range(200, 300))
        
        result = preprocess_for_training(
            X, y, 
            test_size=0.2, 
            normalize=True,
            create_sequences_flag=False
        )
        
        # Check all required keys are present
        assert 'X_train' in result
        assert 'X_test' in result
        assert 'y_train' in result
        assert 'y_test' in result
        assert 'scaler' in result
        
        # Check sizes
        assert len(result['X_train']) == 80
        assert len(result['X_test']) == 20
    
    def test_pipeline_with_sequences(self):
        """Test pipeline with sequence creation"""
        X = pd.DataFrame({
            'feature1': range(100),
            'feature2': range(100, 200)
        })
        y = pd.Series(range(200, 300))
        
        result = preprocess_for_training(
            X, y,
            test_size=0.2,
            normalize=True,
            create_sequences_flag=True,
            sequence_length=10
        )
        
        # Check sequence keys are present
        assert 'sequences_train' in result
        assert 'sequences_test' in result
        assert 'y_train_seq' in result
        assert 'y_test_seq' in result
        
        # Check sequence shapes
        assert result['sequences_train'].shape == (71, 10, 2)  # 80 - 10 + 1 = 71
        assert result['sequences_test'].shape == (11, 10, 2)   # 20 - 10 + 1 = 11
        
        # Check y shapes match sequences
        assert len(result['y_train_seq']) == 71
        assert len(result['y_test_seq']) == 11
    
    def test_pipeline_without_normalization(self):
        """Test pipeline without normalization"""
        X = pd.DataFrame({
            'feature1': [100, 110, 120],
            'feature2': [1000, 1100, 1200]
        })
        y = pd.Series([10, 20, 30])
        
        result = preprocess_for_training(
            X, y,
            test_size=0.33,
            normalize=False
        )
        
        # Check that values are not normalized
        assert result['X_train']['feature1'].mean() > 50  # Not normalized (should be ~0 if normalized)
        
        # Check scaler is None
        assert result['scaler'] is None
    
    def test_pipeline_preserves_temporal_order(self):
        """Test that pipeline preserves temporal order (no data leakage)"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        X = pd.DataFrame({'feature': range(100)}, index=dates)
        y = pd.Series(range(100), index=dates)
        
        result = preprocess_for_training(X, y, test_size=0.2)
        
        # Check temporal order
        assert result['X_train'].index[-1] < result['X_test'].index[0]
        
        # Check no data leakage
        train_indices = set(result['X_train'].index)
        test_indices = set(result['X_test'].index)
        assert len(train_indices.intersection(test_indices)) == 0


class TestDataLeakagePrevention:
    """Tests specifically for data leakage prevention"""
    
    def test_no_future_data_in_training(self):
        """Verify that training data never contains future information"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        X = pd.DataFrame({'feature': range(100)}, index=dates)
        y = pd.Series(range(100), index=dates)
        
        X_train, X_test, y_train, y_test = split_train_test(X, y, test_size=0.2)
        
        # Training data should only contain past dates
        # Test data should only contain future dates
        latest_train_date = X_train.index.max()
        earliest_test_date = X_test.index.min()
        
        assert latest_train_date < earliest_test_date
    
    def test_cv_splitter_no_leakage(self):
        """Verify CV splitter doesn't cause data leakage"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        X = pd.DataFrame({'feature': range(100)}, index=dates)
        splitter = get_time_series_cv_splitter(n_splits=5)
        
        for train_idx, test_idx in splitter.split(X):
            # All training indices should be < all test indices
            assert max(train_idx) < min(test_idx)
            
            # No overlap
            assert len(set(train_idx).intersection(set(test_idx))) == 0
    
    def test_sequences_no_leakage(self):
        """Verify sequence creation doesn't cause data leakage"""
        X = pd.DataFrame({'feature': range(100)})
        sequences = create_sequences(X, sequence_length=10)
        
        # Each sequence should contain consecutive data only
        # Check first sequence
        assert np.array_equal(sequences[0, :, 0], np.arange(0, 10))
        
        # Check that sequences don't skip forward in time
        for i in range(len(sequences) - 1):
            # Each sequence should start 1 step after the previous
            assert sequences[i+1, 0, 0] == sequences[i, 1, 0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

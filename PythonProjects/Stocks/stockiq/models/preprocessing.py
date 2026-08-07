"""
Data Preprocessing Module for ML Pipeline

This module provides data preprocessing capabilities for the ML pipeline,
including feature normalization, sequence creation for time-series models,
train/test splitting, and time-series cross-validation.

Requirements: 3.6, 13.1-13.3
"""

import pandas as pd
import numpy as np
from typing import Tuple, List
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import logging

# Configure logging
logger = logging.getLogger(__name__)


def normalize_features(X: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize features using StandardScaler for consistent scaling.
    
    StandardScaler transforms features by removing the mean and scaling to unit variance:
    z = (x - mean) / std_dev
    
    This ensures all features are on the same scale, which is critical for:
    - Neural networks (gradient descent optimization)
    - Distance-based algorithms (KNN, SVM)
    - Regularized models (Ridge, Lasso)
    
    Args:
        X: DataFrame with features to normalize
        
    Returns:
        DataFrame with normalized features (same index and columns as input)
        
    Example:
        >>> import pandas as pd
        >>> data = pd.DataFrame({'price': [100, 110, 120], 'volume': [1000, 1100, 1200]})
        >>> normalized = normalize_features(data)
        >>> print(normalized)
        
    Notes:
        - Preserves DataFrame structure (index and column names)
        - Returns a new DataFrame (does not modify input)
        - Handles NaN values by fitting scaler only on non-NaN data
    """
    if X.empty:
        logger.warning("Empty DataFrame provided to normalize_features")
        return X.copy()
    
    logger.info(f"Normalizing {X.shape[1]} features across {X.shape[0]} samples")
    
    # Initialize StandardScaler
    scaler = StandardScaler()
    
    # Fit and transform the data
    # StandardScaler handles NaN values by ignoring them during fit
    X_normalized = scaler.fit_transform(X)
    
    # Convert back to DataFrame with original index and columns
    result = pd.DataFrame(
        X_normalized,
        index=X.index,
        columns=X.columns
    )
    
    logger.info(f"Normalization complete. Mean: {result.mean().mean():.6f}, Std: {result.std().mean():.6f}")
    
    return result


def create_sequences(data: pd.DataFrame, sequence_length: int = 60) -> np.ndarray:
    """
    Create sequences for time-series models (LSTM, GRU).
    
    Transforms a DataFrame into overlapping sequences suitable for recurrent neural networks.
    Each sequence contains `sequence_length` consecutive time steps, and the sequences
    overlap by sliding a 1-step window through the data.
    
    Example:
        Given data with 100 rows and sequence_length=60:
        - Sequence 0: rows 0-59 (60 time steps)
        - Sequence 1: rows 1-60 (60 time steps)
        - Sequence 2: rows 2-61 (60 time steps)
        - ...
        - Sequence 40: rows 40-99 (60 time steps)
        
        Output shape: (41, 60, num_features)
        
    Args:
        data: DataFrame with time-series data (rows = time steps, columns = features)
        sequence_length: Number of time steps in each sequence (default 60)
        
    Returns:
        3D numpy array with shape (num_sequences, sequence_length, num_features)
        - num_sequences = len(data) - sequence_length + 1
        - sequence_length = input parameter
        - num_features = data.shape[1]
        
    Example:
        >>> import pandas as pd
        >>> data = pd.DataFrame({'feature1': range(100), 'feature2': range(100, 200)})
        >>> sequences = create_sequences(data, sequence_length=60)
        >>> print(sequences.shape)  # (41, 60, 2)
        >>> print(sequences[0])  # First sequence (rows 0-59)
        
    Raises:
        ValueError: If sequence_length is greater than or equal to len(data)
        ValueError: If data is empty or sequence_length < 1
        
    Notes:
        - Temporal order is preserved (earlier rows = earlier time steps)
        - No data leakage: sequences only contain past data
        - Suitable for LSTM, GRU, and other RNN architectures
    """
    if data.empty:
        raise ValueError("Cannot create sequences from empty DataFrame")
    
    if sequence_length < 1:
        raise ValueError(f"sequence_length must be >= 1, got {sequence_length}")
    
    if sequence_length >= len(data):
        raise ValueError(
            f"sequence_length ({sequence_length}) must be less than data length ({len(data)})"
        )
    
    logger.info(f"Creating sequences with length {sequence_length} from data with shape {data.shape}")
    
    # Convert DataFrame to numpy array for efficient indexing
    data_array = data.values
    
    # Calculate number of sequences
    num_sequences = len(data) - sequence_length + 1
    num_features = data.shape[1]
    
    # Pre-allocate array for sequences
    sequences = np.zeros((num_sequences, sequence_length, num_features))
    
    # Create sequences using sliding window
    for i in range(num_sequences):
        sequences[i] = data_array[i:i + sequence_length]
    
    logger.info(f"Created {num_sequences} sequences with shape ({sequence_length}, {num_features})")
    logger.info(f"Output shape: {sequences.shape}")
    
    return sequences


def split_train_test(
    X: pd.DataFrame, 
    y: pd.Series, 
    test_size: float = 0.2
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Split data into train and test sets while respecting temporal ordering.
    
    For time-series data, we CANNOT use random shuffling because:
    1. It causes data leakage (future data in training set)
    2. It breaks temporal dependencies
    3. It doesn't reflect real-world prediction scenarios
    
    This function performs a temporal split:
    - First (1 - test_size) portion → training set
    - Last (test_size) portion → test set
    
    This ensures no future data leaks into training and mimics real deployment
    where we train on historical data and predict on future data.
    
    Args:
        X: DataFrame with features
        y: Series with target variable (must have same index as X)
        test_size: Fraction of data to use for testing (default 0.2 = 20%)
        
    Returns:
        Tuple of (X_train, X_test, y_train, y_test)
        - X_train: Training features
        - X_test: Test features
        - y_train: Training targets
        - y_test: Test targets
        
    Example:
        >>> import pandas as pd
        >>> X = pd.DataFrame({'feature1': range(100), 'feature2': range(100, 200)})
        >>> y = pd.Series(range(200, 300))
        >>> X_train, X_test, y_train, y_test = split_train_test(X, y, test_size=0.2)
        >>> print(len(X_train))  # 80
        >>> print(len(X_test))   # 20
        
    Raises:
        ValueError: If X and y have different lengths
        ValueError: If test_size is not between 0 and 1
        ValueError: If test_size would result in empty train or test set
        
    Notes:
        - Preserves temporal order (no shuffling)
        - Ensures no data leakage
        - Test set always contains the most recent data
        - Index is preserved in all output DataFrames/Series
    """
    if len(X) != len(y):
        raise ValueError(f"X and y must have same length. Got X: {len(X)}, y: {len(y)}")
    
    if not 0 < test_size < 1:
        raise ValueError(f"test_size must be between 0 and 1, got {test_size}")
    
    # Calculate split index
    split_idx = int(len(X) * (1 - test_size))
    
    if split_idx <= 0 or split_idx >= len(X):
        raise ValueError(
            f"test_size={test_size} results in invalid split. "
            f"Train size: {split_idx}, Test size: {len(X) - split_idx}"
        )
    
    logger.info(f"Splitting {len(X)} samples into train/test with test_size={test_size}")
    logger.info(f"Train samples: {split_idx} ({(1-test_size)*100:.1f}%)")
    logger.info(f"Test samples: {len(X) - split_idx} ({test_size*100:.1f}%)")
    
    # Perform temporal split
    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]
    
    # Log date ranges if index is datetime
    if isinstance(X.index, pd.DatetimeIndex):
        logger.info(f"Train date range: {X_train.index[0]} to {X_train.index[-1]}")
        logger.info(f"Test date range: {X_test.index[0]} to {X_test.index[-1]}")
    
    return X_train, X_test, y_train, y_test


def get_time_series_cv_splitter(n_splits: int = 5) -> TimeSeriesSplit:
    """
    Create a time-series cross-validation splitter with 5 folds.
    
    Time-series cross-validation is different from standard K-fold CV:
    
    Standard K-Fold (WRONG for time-series):
    - Randomly splits data into K folds
    - Causes data leakage (training on future, testing on past)
    
    Time-Series Split (CORRECT for time-series):
    - Respects temporal order
    - Each fold uses all past data for training
    - Tests on the immediate future period
    
    Example with n_splits=5:
    
    Fold 1: Train [----]           Test [--]
    Fold 2: Train [--------]       Test [--]
    Fold 3: Train [------------]   Test [--]
    Fold 4: Train [----------------] Test [--]
    Fold 5: Train [--------------------] Test [--]
    
    Each fold:
    - Training set grows (includes more historical data)
    - Test set always follows training set (no overlap)
    - No data leakage
    
    Args:
        n_splits: Number of cross-validation folds (default 5)
        
    Returns:
        TimeSeriesSplit object configured for time-series CV
        
    Example:
        >>> import pandas as pd
        >>> from sklearn.ensemble import RandomForestRegressor
        >>> 
        >>> X = pd.DataFrame({'feature': range(100)})
        >>> y = pd.Series(range(100))
        >>> 
        >>> cv_splitter = get_time_series_cv_splitter(n_splits=5)
        >>> 
        >>> for fold, (train_idx, test_idx) in enumerate(cv_splitter.split(X)):
        ...     X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        ...     y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        ...     
        ...     model = RandomForestRegressor()
        ...     model.fit(X_train, y_train)
        ...     score = model.score(X_test, y_test)
        ...     print(f"Fold {fold+1}: Train size={len(train_idx)}, Test size={len(test_idx)}, Score={score:.4f}")
        
    Usage with cross_val_score:
        >>> from sklearn.model_selection import cross_val_score
        >>> from sklearn.ensemble import RandomForestRegressor
        >>> 
        >>> model = RandomForestRegressor()
        >>> cv_splitter = get_time_series_cv_splitter(n_splits=5)
        >>> scores = cross_val_score(model, X, y, cv=cv_splitter)
        >>> print(f"CV Scores: {scores}")
        >>> print(f"Mean CV Score: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")
        
    Notes:
        - Default n_splits=5 provides good balance between training data and validation
        - Training set grows with each fold (walk-forward validation)
        - Test set size is approximately constant across folds
        - Ensures no future data leaks into training
        - Compatible with scikit-learn's cross_val_score and GridSearchCV
    """
    if n_splits < 2:
        raise ValueError(f"n_splits must be >= 2, got {n_splits}")
    
    logger.info(f"Creating TimeSeriesSplit with {n_splits} folds")
    logger.info("Each fold will use expanding training window (walk-forward validation)")
    
    # Create TimeSeriesSplit object
    cv_splitter = TimeSeriesSplit(n_splits=n_splits)
    
    return cv_splitter


def preprocess_for_training(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2,
    normalize: bool = True,
    create_sequences_flag: bool = False,
    sequence_length: int = 60
) -> dict:
    """
    Complete preprocessing pipeline combining normalization, splitting, and optional sequencing.
    
    This is a convenience function that orchestrates the entire preprocessing workflow:
    1. Optional normalization using StandardScaler
    2. Train/test split respecting temporal order
    3. Optional sequence creation for RNN models
    
    Args:
        X: DataFrame with features
        y: Series with target variable
        test_size: Fraction of data for testing (default 0.2)
        normalize: Whether to normalize features (default True)
        create_sequences_flag: Whether to create sequences for RNNs (default False)
        sequence_length: Length of sequences if create_sequences_flag=True (default 60)
        
    Returns:
        Dictionary with keys:
        - 'X_train': Training features
        - 'X_test': Test features
        - 'y_train': Training targets
        - 'y_test': Test targets
        - 'scaler': Fitted StandardScaler (if normalize=True)
        - 'sequences_train': Training sequences (if create_sequences_flag=True)
        - 'sequences_test': Test sequences (if create_sequences_flag=True)
        
    Example:
        >>> import pandas as pd
        >>> X = pd.DataFrame({'feature1': range(100), 'feature2': range(100, 200)})
        >>> y = pd.Series(range(200, 300))
        >>> 
        >>> # Standard preprocessing
        >>> result = preprocess_for_training(X, y, test_size=0.2, normalize=True)
        >>> X_train, X_test = result['X_train'], result['X_test']
        >>> y_train, y_test = result['y_train'], result['y_test']
        >>> 
        >>> # For LSTM models
        >>> result = preprocess_for_training(
        ...     X, y, test_size=0.2, normalize=True, 
        ...     create_sequences_flag=True, sequence_length=60
        ... )
        >>> sequences_train = result['sequences_train']
        >>> sequences_test = result['sequences_test']
    """
    logger.info("Starting preprocessing pipeline")
    logger.info(f"Input shape: X={X.shape}, y={y.shape}")
    
    result = {}
    
    # Step 1: Normalize features (optional)
    if normalize:
        logger.info("Step 1: Normalizing features")
        X_normalized = normalize_features(X)
        result['scaler'] = StandardScaler().fit(X)  # Store fitted scaler for inverse transform
    else:
        logger.info("Step 1: Skipping normalization")
        X_normalized = X.copy()
        result['scaler'] = None
    
    # Step 2: Split into train/test sets
    logger.info(f"Step 2: Splitting into train/test with test_size={test_size}")
    X_train, X_test, y_train, y_test = split_train_test(X_normalized, y, test_size=test_size)
    
    result['X_train'] = X_train
    result['X_test'] = X_test
    result['y_train'] = y_train
    result['y_test'] = y_test
    
    # Step 3: Create sequences (optional, for RNN models)
    if create_sequences_flag:
        logger.info(f"Step 3: Creating sequences with length {sequence_length}")
        
        # Create sequences for training data
        if len(X_train) > sequence_length:
            sequences_train = create_sequences(X_train, sequence_length=sequence_length)
            result['sequences_train'] = sequences_train
            
            # Adjust y_train to match sequences (remove first sequence_length-1 samples)
            result['y_train_seq'] = y_train.iloc[sequence_length-1:].values
            logger.info(f"Training sequences: {sequences_train.shape}")
        else:
            logger.warning(f"Training set too small for sequences (len={len(X_train)}, need >{sequence_length})")
            result['sequences_train'] = None
            result['y_train_seq'] = None
        
        # Create sequences for test data
        if len(X_test) > sequence_length:
            sequences_test = create_sequences(X_test, sequence_length=sequence_length)
            result['sequences_test'] = sequences_test
            
            # Adjust y_test to match sequences
            result['y_test_seq'] = y_test.iloc[sequence_length-1:].values
            logger.info(f"Test sequences: {sequences_test.shape}")
        else:
            logger.warning(f"Test set too small for sequences (len={len(X_test)}, need >{sequence_length})")
            result['sequences_test'] = None
            result['y_test_seq'] = None
    else:
        logger.info("Step 3: Skipping sequence creation")
    
    logger.info("Preprocessing pipeline complete")
    return result


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    print("Data Preprocessing Module - Example Usage\n")
    print("=" * 60)
    
    # Create sample data
    print("\n1. Creating sample time-series data...")
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    X = pd.DataFrame({
        'feature1': np.random.randn(100).cumsum() + 100,
        'feature2': np.random.randn(100).cumsum() + 50,
        'feature3': np.random.randn(100) * 10,
    }, index=dates)
    
    y = pd.Series(np.random.randn(100).cumsum() + 200, index=dates)
    
    print(f"Created X: {X.shape}, y: {y.shape}")
    print(f"Date range: {X.index[0]} to {X.index[-1]}")
    
    # Test normalize_features
    print("\n2. Testing normalize_features...")
    X_normalized = normalize_features(X)
    print(f"Original - Mean: {X.mean().mean():.2f}, Std: {X.std().mean():.2f}")
    print(f"Normalized - Mean: {X_normalized.mean().mean():.6f}, Std: {X_normalized.std().mean():.6f}")
    
    # Test split_train_test
    print("\n3. Testing split_train_test...")
    X_train, X_test, y_train, y_test = split_train_test(X_normalized, y, test_size=0.2)
    print(f"Train: X={X_train.shape}, y={y_train.shape}")
    print(f"Test: X={X_test.shape}, y={y_test.shape}")
    print(f"Train dates: {X_train.index[0]} to {X_train.index[-1]}")
    print(f"Test dates: {X_test.index[0]} to {X_test.index[-1]}")
    
    # Test create_sequences
    print("\n4. Testing create_sequences...")
    sequences = create_sequences(X_train, sequence_length=10)
    print(f"Sequences shape: {sequences.shape}")
    print(f"(num_sequences, sequence_length, num_features)")
    
    # Test get_time_series_cv_splitter
    print("\n5. Testing get_time_series_cv_splitter...")
    cv_splitter = get_time_series_cv_splitter(n_splits=5)
    print(f"Created TimeSeriesSplit with 5 folds")
    print("\nFold splits:")
    for fold, (train_idx, test_idx) in enumerate(cv_splitter.split(X)):
        print(f"  Fold {fold+1}: Train size={len(train_idx)}, Test size={len(test_idx)}")
    
    # Test complete preprocessing pipeline
    print("\n6. Testing complete preprocessing pipeline...")
    result = preprocess_for_training(
        X, y, 
        test_size=0.2, 
        normalize=True,
        create_sequences_flag=True,
        sequence_length=10
    )
    print("\nPipeline results:")
    for key, value in result.items():
        if value is not None:
            if isinstance(value, (pd.DataFrame, pd.Series)):
                print(f"  {key}: shape={value.shape}")
            elif isinstance(value, np.ndarray):
                print(f"  {key}: shape={value.shape}")
            else:
                print(f"  {key}: {type(value).__name__}")
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")

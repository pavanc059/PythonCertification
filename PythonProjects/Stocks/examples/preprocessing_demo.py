"""
Data Preprocessing Demo

This example demonstrates the use of the preprocessing module for preparing
data for ML models, including:
- Feature normalization
- Time-series sequence creation for LSTM models
- Train/test splitting with temporal ordering
- Time-series cross-validation

Requirements: 3.6, 13.1-13.3
"""

import pandas as pd
import numpy as np
from stockiq.models.features import create_feature_matrix
from stockiq.models.preprocessing import (
    normalize_features,
    create_sequences,
    split_train_test,
    get_time_series_cv_splitter,
    preprocess_for_training,
)
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score


def demo_basic_preprocessing():
    """Demonstrate basic preprocessing workflow."""
    print("=" * 80)
    print("DEMO 1: Basic Preprocessing Workflow")
    print("=" * 80)
    
    # Create sample feature data
    print("\n1. Creating feature matrix for AAPL...")
    features = create_feature_matrix('AAPL', lookback_days=90)
    print(f"   Feature matrix shape: {features.shape}")
    print(f"   Columns: {len(features.columns)}")
    
    # Select features for training (remove target and original price columns)
    feature_cols = [col for col in features.columns 
                    if not col.startswith(('target_', 'Open', 'High', 'Low', 'Close', 'Volume'))]
    
    X = features[feature_cols].dropna()
    y = features.loc[X.index, 'target_return']
    
    print(f"   Training data: X={X.shape}, y={y.shape}")
    
    # Normalize features
    print("\n2. Normalizing features...")
    X_normalized = normalize_features(X)
    print(f"   Before: mean={X.mean().mean():.2f}, std={X.std().mean():.2f}")
    print(f"   After: mean={X_normalized.mean().mean():.6f}, std={X_normalized.std(ddof=0).mean():.6f}")
    
    # Split into train/test
    print("\n3. Splitting into train/test sets...")
    X_train, X_test, y_train, y_test = split_train_test(X_normalized, y, test_size=0.2)
    print(f"   Train: {len(X_train)} samples")
    print(f"   Test: {len(X_test)} samples")
    print(f"   Train period: {X_train.index[0].date()} to {X_train.index[-1].date()}")
    print(f"   Test period: {X_test.index[0].date()} to {X_test.index[-1].date()}")
    
    print("\n✓ Basic preprocessing complete!")


def demo_sequence_creation():
    """Demonstrate sequence creation for LSTM models."""
    print("\n" + "=" * 80)
    print("DEMO 2: Sequence Creation for LSTM/RNN Models")
    print("=" * 80)
    
    # Create sample feature data
    print("\n1. Creating feature matrix...")
    features = create_feature_matrix('MSFT', lookback_days=120)
    
    feature_cols = [col for col in features.columns 
                    if not col.startswith(('target_', 'Open', 'High', 'Low', 'Close', 'Volume'))]
    
    X = features[feature_cols].dropna()
    y = features.loc[X.index, 'target_direction']
    
    print(f"   Data shape: X={X.shape}, y={y.shape}")
    
    # Normalize and split
    print("\n2. Preprocessing data...")
    X_normalized = normalize_features(X)
    X_train, X_test, y_train, y_test = split_train_test(X_normalized, y, test_size=0.2)
    
    # Create sequences for LSTM
    print("\n3. Creating sequences for LSTM...")
    sequence_length = 10
    sequences_train = create_sequences(X_train, sequence_length=sequence_length)
    sequences_test = create_sequences(X_test, sequence_length=sequence_length)
    
    print(f"   Training sequences: {sequences_train.shape}")
    print(f"   Test sequences: {sequences_test.shape}")
    print(f"   Shape interpretation: (num_sequences, time_steps, features)")
    
    # Adjust y to match sequences
    y_train_seq = y_train.iloc[sequence_length-1:].values
    y_test_seq = y_test.iloc[sequence_length-1:].values
    
    print(f"\n   Adjusted targets:")
    print(f"   y_train_seq: {y_train_seq.shape}")
    print(f"   y_test_seq: {y_test_seq.shape}")
    
    print("\n✓ Sequences ready for LSTM training!")
    print("\n   Example LSTM input shape: (batch_size, 10, num_features)")


def demo_time_series_cv():
    """Demonstrate time-series cross-validation."""
    print("\n" + "=" * 80)
    print("DEMO 3: Time-Series Cross-Validation")
    print("=" * 80)
    
    # Create sample feature data
    print("\n1. Creating feature matrix...")
    features = create_feature_matrix('GOOGL', lookback_days=100)
    
    feature_cols = [col for col in features.columns 
                    if not col.startswith(('target_', 'Open', 'High', 'Low', 'Close', 'Volume'))]
    
    X = features[feature_cols].dropna()
    y = features.loc[X.index, 'target_direction']
    
    # Normalize
    X_normalized = normalize_features(X)
    
    print(f"   Data shape: X={X_normalized.shape}, y={y.shape}")
    
    # Create time-series CV splitter
    print("\n2. Setting up time-series cross-validation...")
    cv_splitter = get_time_series_cv_splitter(n_splits=5)
    
    # Train model with cross-validation
    print("\n3. Training with cross-validation...")
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    
    print("\n   Fold Results:")
    scores = cross_val_score(model, X_normalized, y, cv=cv_splitter, scoring='r2')
    
    for fold, score in enumerate(scores, 1):
        print(f"   Fold {fold}: R² = {score:.4f}")
    
    print(f"\n   Mean R²: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")
    
    print("\n✓ Cross-validation complete!")
    print("\n   Note: Each fold uses expanding training window (walk-forward validation)")


def demo_complete_pipeline():
    """Demonstrate complete preprocessing pipeline."""
    print("\n" + "=" * 80)
    print("DEMO 4: Complete Preprocessing Pipeline")
    print("=" * 80)
    
    # Create sample feature data
    print("\n1. Creating feature matrix...")
    features = create_feature_matrix('TSLA', lookback_days=100)
    
    feature_cols = [col for col in features.columns 
                    if not col.startswith(('target_', 'Open', 'High', 'Low', 'Close', 'Volume'))]
    
    X = features[feature_cols].dropna()
    y = features.loc[X.index, 'target_return']
    
    print(f"   Input shape: X={X.shape}, y={y.shape}")
    
    # Use complete pipeline
    print("\n2. Running complete preprocessing pipeline...")
    result = preprocess_for_training(
        X, y,
        test_size=0.2,
        normalize=True,
        create_sequences_flag=True,
        sequence_length=15
    )
    
    print("\n   Pipeline outputs:")
    for key, value in result.items():
        if value is not None:
            if isinstance(value, (pd.DataFrame, pd.Series)):
                print(f"   - {key}: DataFrame/Series with shape {value.shape}")
            elif isinstance(value, np.ndarray):
                print(f"   - {key}: numpy array with shape {value.shape}")
            else:
                print(f"   - {key}: {type(value).__name__}")
    
    print("\n✓ Complete pipeline executed successfully!")
    print("\n   Ready for:")
    print("   - Traditional ML: Use X_train, X_test, y_train, y_test")
    print("   - LSTM/RNN: Use sequences_train, sequences_test, y_train_seq, y_test_seq")


def demo_data_leakage_prevention():
    """Demonstrate that preprocessing prevents data leakage."""
    print("\n" + "=" * 80)
    print("DEMO 5: Data Leakage Prevention")
    print("=" * 80)
    
    # Create time-indexed data
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    X = pd.DataFrame({
        'feature1': range(100),
        'feature2': range(100, 200),
    }, index=dates)
    y = pd.Series(range(200, 300), index=dates)
    
    print("\n1. Splitting data with temporal ordering...")
    X_train, X_test, y_train, y_test = split_train_test(X, y, test_size=0.2)
    
    print(f"   Training period: {X_train.index[0].date()} to {X_train.index[-1].date()}")
    print(f"   Test period: {X_test.index[0].date()} to {X_test.index[-1].date()}")
    
    # Verify no overlap
    train_dates = set(X_train.index)
    test_dates = set(X_test.index)
    overlap = train_dates & test_dates
    
    print(f"\n2. Checking for data leakage...")
    print(f"   Training set dates: {len(train_dates)}")
    print(f"   Test set dates: {len(test_dates)}")
    print(f"   Overlap: {len(overlap)} dates")
    
    # Verify test comes after train
    last_train_date = X_train.index[-1]
    first_test_date = X_test.index[0]
    
    print(f"\n3. Verifying temporal order...")
    print(f"   Last training date: {last_train_date.date()}")
    print(f"   First test date: {first_test_date.date()}")
    print(f"   Test follows train: {first_test_date > last_train_date}")
    
    if first_test_date > last_train_date and len(overlap) == 0:
        print("\n✓ No data leakage detected!")
        print("   All test data comes after training data (temporal ordering preserved)")
    else:
        print("\n✗ WARNING: Potential data leakage!")


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "DATA PREPROCESSING DEMO" + " " * 35 + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        # Run all demos
        demo_basic_preprocessing()
        demo_sequence_creation()
        demo_time_series_cv()
        demo_complete_pipeline()
        demo_data_leakage_prevention()
        
        print("\n" + "=" * 80)
        print("ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nKey Takeaways:")
        print("1. Always normalize features for neural networks and distance-based algorithms")
        print("2. Use sequence creation for LSTM/RNN models (3D input required)")
        print("3. Use temporal train/test split to prevent data leakage")
        print("4. Use time-series cross-validation for hyperparameter tuning")
        print("5. The complete pipeline handles all steps automatically")
        
    except Exception as e:
        print(f"\n✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()

"""
Deep Learning Models Package

This package provides deep learning models for time-series prediction
and advanced market analysis.

Modules:
- lstm: LSTM neural networks for time-series price prediction
- transformer: Transformer models for multi-variate market analysis
- autoencoder: Anomaly detection using autoencoders and isolation forests
"""

from .lstm import LSTMPredictor, Prediction
from .transformer import TransformerPredictor
from .autoencoder import (
    AnomalyDetector,
    IsolationForestDetector,
    AutoencoderDetector,
    AnomalyResult
)

__all__ = [
    'LSTMPredictor',
    'TransformerPredictor',
    'Prediction',
    'AnomalyDetector',
    'IsolationForestDetector',
    'AutoencoderDetector',
    'AnomalyResult'
]

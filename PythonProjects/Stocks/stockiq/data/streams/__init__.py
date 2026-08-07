"""
Real-time data streaming components.

This module provides WebSocket-based streaming for real-time market data
with automatic reconnection and sub-second latency requirements.
"""

from .websocket import WebSocketStream, StreamStatus, ConnectionConfig

__all__ = ['WebSocketStream', 'StreamStatus', 'ConnectionConfig']

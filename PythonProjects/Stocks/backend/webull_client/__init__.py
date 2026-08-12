"""
webull_client package — public API surface.

Exports:
  WebullClient            — authenticated wrapper around the webull PyPI package
  WebullUnavailableError  — raised when Webull cannot be reached / session invalid
  WebullQuoteData         — normalized internal quote type

Note: WebullClient and WebullUnavailableError are implemented in client.py (task 2.3).
      Importing them here will fail until that file is created.
"""

from .types import WebullQuoteData

# WebullClient and WebullUnavailableError are defined in client.py (task 2.3).
# They are listed here so the public API is clear; import them after client.py exists.
try:
    from .client import WebullClient, WebullUnavailableError
except ImportError:
    # client.py has not been created yet (pending task 2.3).
    # This allows the package to be imported for types before the client is implemented.
    WebullClient = None  # type: ignore[assignment,misc]
    WebullUnavailableError = None  # type: ignore[assignment,misc]

__all__ = [
    "WebullClient",
    "WebullUnavailableError",
    "WebullQuoteData",
]

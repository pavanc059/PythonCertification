"""
backend/state.py — shared singleton state.

Avoids circular imports between main.py and router modules.
main.py calls set_webull_client(client) at startup;
router modules call get_webull_client() to retrieve the instance.

Requirements: 13.1, 13.2, 13.3
"""

from typing import Optional

# Module-level variable; populated by main.py on_event("startup")
_webull_client: Optional[object] = None


def set_webull_client(client) -> None:
    """Store the WebullClient singleton created at startup."""
    global _webull_client
    _webull_client = client


def get_webull_client():
    """Return the WebullClient singleton, or None if not initialised."""
    return _webull_client

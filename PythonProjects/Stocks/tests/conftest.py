"""Shared pytest configuration for the test suite.

Registers Hypothesis profiles so the property-based tests run with a smaller
number of generated examples by default, keeping the suite fast. The profile
can be overridden via the ``HYPOTHESIS_PROFILE`` environment variable, e.g.::

    HYPOTHESIS_PROFILE=thorough python -m pytest

Available profiles:
    fast      - 10 examples per property (quick local runs, the default)
    dev       - 25 examples per property
    thorough  - 200 examples per property (pre-merge / CI deep checks)

Note: an explicit ``@settings(max_examples=N)`` on an individual test still
overrides the active profile. The high-count decorators in the suite have been
lowered so this profile governs the overall runtime.
"""

import os

from hypothesis import HealthCheck, settings

# Quick local default: few examples, no per-example deadline so slower
# financial calculations are not flagged.
settings.register_profile(
    "fast",
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

settings.register_profile(
    "dev",
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

settings.register_profile(
    "thorough",
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "fast"))

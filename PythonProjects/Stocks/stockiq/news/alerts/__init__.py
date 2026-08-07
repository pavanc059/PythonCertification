"""
News alert detection and delivery subsystem.

Modules:
- detector.py   : Detect alert-worthy news events
- prioritizer.py: Prioritize and group alerts by impact
- notifier.py   : Deliver alerts via multiple channels
- penny_alerts.py: Penny-stock-specific alert detection
"""

from .detector import NewsAlertDetector, NewsAlert, AlertType
from .prioritizer import AlertGroup, calculate_priority, group_related_alerts
from .notifier import AlertNotifier, UserNotificationSettings, SUPPORTED_CHANNELS, VALID_SENSITIVITIES
from .penny_alerts import (
    detect_momentum_threshold,
    detect_high_priority_gain,
    detect_pump_dump_warning,
    detect_insider_activity_alert,
    HIGH_PRIORITY_GAIN_THRESHOLD,
    PUMP_DUMP_SUSPICION_THRESHOLD,
)

__all__ = [
    "NewsAlertDetector",
    "NewsAlert",
    "AlertType",
    "AlertGroup",
    "calculate_priority",
    "group_related_alerts",
    "AlertNotifier",
    "UserNotificationSettings",
    "SUPPORTED_CHANNELS",
    "VALID_SENSITIVITIES",
    "detect_momentum_threshold",
    "detect_high_priority_gain",
    "detect_pump_dump_warning",
    "detect_insider_activity_alert",
    "HIGH_PRIORITY_GAIN_THRESHOLD",
    "PUMP_DUMP_SUSPICION_THRESHOLD",
]

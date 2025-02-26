from typing import Dict, Any
from dataclasses import dataclass
from datetime import timedelta

@dataclass
class NotificationConfig:
    """Configuration for the notification system"""
    # WebSocket settings
    WEBSOCKET_HOST: str = "localhost"
    WEBSOCKET_PORT: int = 8000
    WEBSOCKET_PATH: str = "/ws/notifications"
    
    # Notification display settings
    NOTIFICATION_DURATION: int = 5  # seconds
    NOTIFICATION_ICON_SIZE: int = 32
    NOTIFICATION_BADGE_SIZE: int = 22
    
    # Notification types and their display properties
    NOTIFICATION_TYPES: Dict[str, Dict[str, Any]] = {
        "new_opportunity": {
            "title": "New Opportunity",
            "icon": "opportunity.png",
            "priority": "high"
        },
        "opportunity_update": {
            "title": "Opportunity Updated",
            "icon": "update.png",
            "priority": "medium"
        },
        "opportunity_status": {
            "title": "Status Change",
            "icon": "status.png",
            "priority": "high"
        },
        "comment": {
            "title": "New Comment",
            "icon": "comment.png",
            "priority": "medium"
        },
        "mention": {
            "title": "You were mentioned",
            "icon": "mention.png",
            "priority": "high"
        },
        "assignment": {
            "title": "Task Assignment",
            "icon": "assignment.png",
            "priority": "high"
        }
    }
    
    # Notification grouping settings
    GROUP_SIMILAR_NOTIFICATIONS: bool = True
    GROUP_TIME_WINDOW: timedelta = timedelta(minutes=5)
    
    # Rate limiting settings
    MAX_NOTIFICATIONS_PER_MINUTE: int = 10
    RATE_LIMIT_RESET_INTERVAL: timedelta = timedelta(minutes=1)
    
    # Persistence settings
    NOTIFICATION_HISTORY_LIMIT: int = 100  # Maximum number of notifications to keep in history
    NOTIFICATION_RETENTION_PERIOD: timedelta = timedelta(days=30)  # How long to keep notifications in DB
    
    # Desktop notification settings
    ENABLE_DESKTOP_NOTIFICATIONS: bool = True
    DESKTOP_NOTIFICATION_POSITION: str = "bottom-right"
    DESKTOP_NOTIFICATION_OPACITY: float = 0.9
    
    # Sound settings
    ENABLE_NOTIFICATION_SOUNDS: bool = True
    NOTIFICATION_SOUND_FILE: str = "notification.wav"
    NOTIFICATION_VOLUME: float = 0.5  # 0.0 to 1.0

# Create a global instance
notification_config = NotificationConfig() 
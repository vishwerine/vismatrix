# Services package for tracker app

# Re-export friendship services for backwards compatibility
from .friendship import are_friends

# Semantic classifier is also available
from .semantic_classifier import classify_text, get_category_metadata, MODEL_AVAILABLE

# iCloud calendar service
from .icloud_calendar_service import ICloudCalendarService

__all__ = [
    'are_friends',
    'classify_text',
    'get_category_metadata',
    'MODEL_AVAILABLE',
    'ICloudCalendarService',
]


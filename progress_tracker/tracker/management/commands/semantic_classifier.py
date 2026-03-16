"""
semantic_classifier.py

DEPRECATED: This file has been moved to tracker/services/semantic_classifier.py

Please update your imports to:
  from tracker.services.semantic_classifier import classify_text

This file is kept for backwards compatibility but will be removed in a future version.
The new location loads models at import time for better performance.
"""

import warnings
warnings.warn(
    "Importing from tracker.management.commands.semantic_classifier is deprecated. "
    "Please use: from tracker.services.semantic_classifier import classify_text",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location for backwards compatibility
from tracker.services.semantic_classifier import classify_text, get_category_metadata, MODEL_AVAILABLE

__all__ = ['classify_text', 'get_category_metadata', 'MODEL_AVAILABLE']


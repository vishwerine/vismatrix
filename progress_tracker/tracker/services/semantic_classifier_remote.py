"""
Remote Semantic Classifier Client

Calls the external classifier microservice instead of loading the model locally.
This avoids gunicorn timeout issues.
"""

import logging
import requests
from typing import List, Tuple, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Configuration - can be set in Django settings
CLASSIFIER_SERVICE_URL = getattr(
    settings, 
    'CLASSIFIER_SERVICE_URL', 
    'http://localhost:8001'
)
CLASSIFIER_TIMEOUT = getattr(settings, 'CLASSIFIER_TIMEOUT', 5)  # 5 second timeout


def is_service_available() -> bool:
    """Check if the classifier service is running and ready"""
    try:
        response = requests.get(
            f"{CLASSIFIER_SERVICE_URL}/health",
            timeout=2
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('model_ready', False)
        return False
    except Exception as e:
        logger.warning(f"Classifier service not available: {str(e)}")
        return False


def classify_text(
    text: str,
    top_k: int = 3,
    unknown_threshold: float = 0.25,
) -> Tuple[str, List[Tuple[str, float]]]:
    """
    Classify text using the remote classifier service.
    
    Returns:
        (best_category, [(category, score), ...])
    """
    try:
        response = requests.post(
            f"{CLASSIFIER_SERVICE_URL}/classify",
            json={
                "text": text,
                "top_k": top_k,
                "unknown_threshold": unknown_threshold,
            },
            timeout=CLASSIFIER_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            return data['category'], data['scores']
        else:
            logger.error(f"Classifier service error: {response.status_code}")
            return "Uncategorized", []
            
    except requests.Timeout:
        logger.error("Classifier service timeout")
        return "Uncategorized", []
    except Exception as e:
        logger.error(f"Classifier service error: {str(e)}")
        return "Uncategorized", []


def get_category_metadata() -> dict:
    """Get category metadata from the service"""
    try:
        response = requests.get(
            f"{CLASSIFIER_SERVICE_URL}/categories",
            timeout=CLASSIFIER_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        return {}
        
    except Exception as e:
        logger.error(f"Failed to get categories: {str(e)}")
        return {}


# For backwards compatibility
MODEL_AVAILABLE = is_service_available()
is_model_available = is_service_available
is_model_loaded = is_service_available

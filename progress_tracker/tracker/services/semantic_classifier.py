"""
semantic_classifier.py

Loads saved category prototypes and provides classify_text(text).

Install:
  pip install gensim numpy

Usage:
  from tracker.services.semantic_classifier import classify_text
  label, top = classify_text("go to gym after work")

Notes:
- Uses the SAME embedding model as in build_prototypes.py.
- Loads prototypes from protos/prototypes.npz and metadata from protos/meta.json.
- Prototypes and embeddings are loaded once at module import time for efficiency.
"""

from __future__ import annotations
import json
import os
import re
import logging
from typing import Dict, List, Tuple, Optional

import numpy as np
import gensim.downloader as api

logger = logging.getLogger(__name__)

# -----------------------------
# Load prototypes + metadata
# -----------------------------
# Use Django's BASE_DIR for consistent paths
from django.conf import settings
if settings.configured:
    PROTOS_DIR = os.path.join(settings.BASE_DIR, "protos")
else:
    # Fallback for non-Django contexts (should rarely happen)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    PROTOS_DIR = os.path.join(BASE_DIR, "protos")

NPZ_PATH = os.path.join(PROTOS_DIR, "prototypes.npz")
META_PATH = os.path.join(PROTOS_DIR, "meta.json")

_word_re = re.compile(r"[a-zA-Z][a-zA-Z']+")


def _load_model():
    """
    Load the semantic classifier model lazily on first use.
    Returns (kv, protos, meta) or (None, None, None) if loading fails.
    """
    try:
        # Load metadata
        if not os.path.exists(META_PATH):
            logger.warning(f"Semantic classifier metadata not found at {META_PATH}")
            return None, None, None
            
        with open(META_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # Load prototypes
        if not os.path.exists(NPZ_PATH):
            logger.warning(f"Semantic classifier prototypes not found at {NPZ_PATH}")
            return None, None, None
            
        npz = np.load(NPZ_PATH)
        protos = {k: npz[k].astype(np.float32) for k in npz.files}

        # Load embeddings model (must match the one used for prototypes)
        model_name = meta["embedding_model"]
        logger.info(f"Loading semantic embedding model: {model_name}")
        kv = api.load(model_name)
        logger.info("Semantic classifier loaded successfully")
        
        return kv, protos, meta
        
    except Exception as e:
        logger.error(f"Failed to load semantic classifier: {str(e)}")
        return None, None, None


# Lazy-loaded globals (loaded on first use, not at import time)
_KV = None
_PROTOS = None
_META = None
_LOAD_ATTEMPTED = False
_LOADING_IN_PROGRESS = False


def _ensure_loaded():
    """Ensure model is loaded (lazy loading with caching)"""
    global _KV, _PROTOS, _META, _LOAD_ATTEMPTED, _LOADING_IN_PROGRESS
    
    if _LOAD_ATTEMPTED or _LOADING_IN_PROGRESS:
        return
    
    _LOADING_IN_PROGRESS = True
    _LOAD_ATTEMPTED = True
    
    try:
        _KV, _PROTOS, _META = _load_model()
    finally:
        _LOADING_IN_PROGRESS = False


def is_model_loaded() -> bool:
    """Check if model is actually loaded in memory (not just files exist)"""
    return _KV is not None and _PROTOS is not None and _META is not None


def is_model_available() -> bool:
    """Check if model files exist (without loading)"""
    return os.path.exists(NPZ_PATH) and os.path.exists(META_PATH)


# For backwards compatibility
MODEL_AVAILABLE = is_model_available()


def _tokenize(text: str) -> List[str]:
    return _word_re.findall(text.lower())


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return -1.0
    return float(np.dot(a, b) / denom)


def _text_to_vec(text: str) -> Optional[np.ndarray]:
    # Model must be loaded before calling this
    if _KV is None:
        return None
        
    toks = _tokenize(text)
    vecs = [_KV[t] for t in toks if t in _KV]
    if not vecs:
        return None
    return np.mean(np.vstack(vecs), axis=0).astype(np.float32)


def classify_text(
    text: str,
    top_k: int = 3,
    unknown_threshold: Optional[float] = 0.25,
    load_if_needed: bool = False,
) -> Tuple[str, List[Tuple[str, float]]]:
    """
    Classify text into a category.
    
    Args:
        text: Text to classify
        top_k: Number of top scores to return
        unknown_threshold: Minimum similarity threshold
        load_if_needed: If True, will load model if not loaded (blocks for 30-180s).
                        If False, returns "Uncategorized" if model not loaded yet.
    
    Returns:
      best_label, top_scores

    unknown_threshold:
      If best similarity < threshold, returns "Uncategorized".
      Tune 0.20–0.35 depending on how strict you want it.
    """
    # Check if model is already loaded
    if not is_model_loaded():
        if load_if_needed:
            # Load model (this will block for 30-180 seconds!)
            _ensure_loaded()
        else:
            # Model not loaded and we're not allowed to load it
            logger.info(f"Semantic classifier not loaded yet, skipping classification for: '{text[:50]}...'")
            return "Uncategorized", []
    
    # At this point model must be loaded
    if _KV is None or not _PROTOS:
        logger.warning("Semantic classifier model not available")
        return "Uncategorized", []

    v = _text_to_vec(text)
    if v is None:
        # No tokens in vocab -> no meaningful embedding
        return "Uncategorized", []

    scores = [(cat, _cosine(v, proto)) for cat, proto in _PROTOS.items()]
    scores.sort(key=lambda x: x[1], reverse=True)

    best_cat, best_score = scores[0]
    if unknown_threshold is not None and best_score < unknown_threshold:
        return "Uncategorized", scores[:top_k]
    return best_cat, scores[:top_k]


def get_category_metadata() -> Dict:
    """
    Optional helper: returns meta.json content (colors etc.)
    """
    _ensure_loaded()
    if not is_model_loaded():
        _ensure_loaded()
    
    if _META is None:
        logger.warning("Semantic classifier model not available")
        return {}
    return _META


def preload_model():
    """
    Explicitly load the model (blocking call, takes 30-180 seconds).
    Use this in a management command or background task to pre-warm the model.
    """
    logger.info("Preloading semantic classifier model...")
    _ensure_loaded()
    if is_model_loaded():
        logger.info("✅ Semantic classifier model loaded successfully")
        return True
    else:
        logger.error("❌ Failed to load semantic classifier model")
        return False
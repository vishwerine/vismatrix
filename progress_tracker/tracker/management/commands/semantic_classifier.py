"""
semantic_classifier.py

Loads saved category prototypes and provides classify_text(text).

Install:
  pip install gensim numpy

Usage:
  from semantic_classifier import classify_text
  label, top = classify_text("go to gym after work")

Notes:
- Uses the SAME embedding model as in build_prototypes.py.
- Loads prototypes from protos/prototypes.npz and metadata from protos/meta.json.
"""

from __future__ import annotations
import json
import os
import re
from typing import Dict, List, Tuple, Optional

import numpy as np
import gensim.downloader as api

# -----------------------------
# Load prototypes + metadata
# -----------------------------
# Get the base directory (progress_tracker/progress_tracker/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PROTOS_DIR = os.path.join(BASE_DIR, "progress_tracker", "protos")
NPZ_PATH = os.path.join(PROTOS_DIR, "prototypes.npz")
META_PATH = os.path.join(PROTOS_DIR, "meta.json")

# lazy-loaded globals (so importing doesn't immediately download models)
_KV = None
_PROTOS: Dict[str, np.ndarray] = {}
_META: Dict = {}

_word_re = re.compile(r"[a-zA-Z][a-zA-Z']+")

def _tokenize(text: str) -> List[str]:
    return _word_re.findall(text.lower())

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return -1.0
    return float(np.dot(a, b) / denom)

def _ensure_loaded():
    global _KV, _PROTOS, _META

    if _PROTOS and _META and _KV is not None:
        return

    # Load metadata
    with open(META_PATH, "r", encoding="utf-8") as f:
        _META = json.load(f)

    # Load prototypes
    npz = np.load(NPZ_PATH)
    _PROTOS = {k: npz[k].astype(np.float32) for k in npz.files}

    # Load embeddings model (must match the one used for prototypes)
    model_name = _META["embedding_model"]
    _KV = api.load(model_name)

def _text_to_vec(text: str) -> Optional[np.ndarray]:
    toks = _tokenize(text)
    vecs = [_KV[t] for t in toks if t in _KV]
    if not vecs:
        return None
    return np.mean(np.vstack(vecs), axis=0).astype(np.float32)

def classify_text(
    text: str,
    top_k: int = 3,
    unknown_threshold: Optional[float] = 0.25,
) -> Tuple[str, List[Tuple[str, float]]]:
    """
    Returns:
      best_label, top_scores

    unknown_threshold:
      If best similarity < threshold, returns "Uncategorized".
      Tune 0.20–0.35 depending on how strict you want it.
    """
    _ensure_loaded()

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
    return _META

"""
Semantic Classifier Microservice

A standalone HTTP API service for text classification.
Runs independently from Django/gunicorn to avoid timeout issues.

Install:
    pip install fastapi uvicorn gensim numpy

Run:
    uvicorn classifier_service:app --host 0.0.0.0 --port 8001

Or with gunicorn (for production):
    gunicorn classifier_service:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001 --timeout 300
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Tuple, Optional
from contextlib import asynccontextmanager
import logging
import os
import json
import re
import numpy as np
import gensim.downloader as api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROTOS_DIR = os.path.join(os.path.dirname(__file__), "progress_tracker", "protos")
NPZ_PATH = os.path.join(PROTOS_DIR, "prototypes.npz")
META_PATH = os.path.join(PROTOS_DIR, "meta.json")

# Global model storage
_KV = None
_PROTOS = None
_META = None
_MODEL_READY = False

_word_re = re.compile(r"[a-zA-Z][a-zA-Z']+")


class ClassificationRequest(BaseModel):
    text: str
    top_k: int = 3
    unknown_threshold: float = 0.25


class ClassificationResponse(BaseModel):
    category: str
    scores: List[Tuple[str, float]]
    model_ready: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown"""
    global _KV, _PROTOS, _META, _MODEL_READY
    
    # Startup
    logger.info("🚀 Loading semantic classifier model...")
    
    try:
        # Load metadata
        if not os.path.exists(META_PATH):
            logger.error(f"Metadata not found at {META_PATH}")
            yield
            return
            
        with open(META_PATH, "r", encoding="utf-8") as f:
            _META = json.load(f)

        # Load prototypes
        if not os.path.exists(NPZ_PATH):
            logger.error(f"Prototypes not found at {NPZ_PATH}")
            yield
            return
            
        npz = np.load(NPZ_PATH)
        _PROTOS = {k: npz[k].astype(np.float32) for k in npz.files}

        # Load embeddings model
        model_name = _META["embedding_model"]
        logger.info(f"Loading embedding model: {model_name} (this may take a while...)")
        _KV = api.load(model_name)
        
        _MODEL_READY = True
        logger.info("✅ Semantic classifier loaded and ready!")
        
    except Exception as e:
        logger.error(f"❌ Failed to load model: {str(e)}")
        _MODEL_READY = False
    
    yield
    
    # Shutdown (cleanup if needed)
    logger.info("Shutting down classifier service...")


app = FastAPI(title="Semantic Classifier API", version="1.0.0", lifespan=lifespan)


def _tokenize(text: str) -> List[str]:
    return _word_re.findall(text.lower())


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return -1.0
    return float(np.dot(a, b) / denom)


def _text_to_vec(text: str) -> Optional[np.ndarray]:
    if _KV is None:
        return None
        
    toks = _tokenize(text)
    vecs = [_KV[t] for t in toks if t in _KV]
    if not vecs:
        return None
    return np.mean(np.vstack(vecs), axis=0).astype(np.float32)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "model_ready": _MODEL_READY,
    }


@app.post("/classify", response_model=ClassificationResponse)
async def classify_text(request: ClassificationRequest):
    """Classify text into a category"""
    
    if not _MODEL_READY:
        return ClassificationResponse(
            category="Uncategorized",
            scores=[],
            model_ready=False
        )
    
    v = _text_to_vec(request.text)
    if v is None:
        return ClassificationResponse(
            category="Uncategorized",
            scores=[],
            model_ready=True
        )

    scores = [(cat, _cosine(v, proto)) for cat, proto in _PROTOS.items()]
    scores.sort(key=lambda x: x[1], reverse=True)

    best_cat, best_score = scores[0]
    
    if best_score < request.unknown_threshold:
        best_cat = "Uncategorized"
    
    return ClassificationResponse(
        category=best_cat,
        scores=scores[:request.top_k],
        model_ready=True
    )


@app.get("/categories")
async def get_categories():
    """Get available categories"""
    if not _MODEL_READY:
        raise HTTPException(status_code=503, detail="Model not ready")
    
    return {
        "categories": _META.get("categories", []),
        "embedding_model": _META.get("embedding_model"),
        "vector_dim": _META.get("vector_dim"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

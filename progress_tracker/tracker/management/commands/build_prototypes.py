"""
build_prototypes.py

Builds category prototype vectors using pretrained FastText word vectors
and saves them locally for fast runtime classification.

Install:
  pip install gensim numpy nltk

Run:
  python build_prototypes.py

Outputs:
  protos/prototypes.npz   (category vectors)
  protos/meta.json        (category metadata + seeds used)
"""

from __future__ import annotations
import os
import json
import re
from typing import Dict, List, Optional

import numpy as np
import gensim.downloader as api

# -----------------------------
# Your categories (given)
# -----------------------------
global_categories = [
    {'name': 'Fitness', 'color': '#10b981'},
    {'name': 'Health', 'color': '#f59e0b'},
    {'name': 'Meditation', 'color': '#8b5cf6'},

    {'name': 'Study', 'color': '#3b82f6'},
    {'name': 'Languages', 'color': '#ef4444'},
    {'name': 'Skills', 'color': '#06b6d4'},

    {'name': 'Job Search', 'color': '#f97316'},
    {'name': 'Interviews', 'color': '#84cc16'},
    {'name': 'Work', 'color': '#1e40af'},
    {'name': 'Freelance', 'color': '#7c3aed'},

    {'name': 'Reading', 'color': '#14b8a6'},
    {'name': 'Journaling', 'color': '#a855f7'},
    {'name': 'Hobbies', 'color': '#f472b6'},

    {'name': 'Goals', 'color': '#059669'},
    {'name': 'Habits', 'color': '#dc2626'},
    {'name': 'Projects', 'color': '#ea580c'},
]

# -----------------------------
# Seed phrases per category
# (edit/extend freely)
# -----------------------------
CATEGORY_SEEDS: Dict[str, List[str]] = {
    "Fitness": ["gym workout", "strength training", "run cardio", "exercise routine", "HIIT session"],
    "Health": ["doctor appointment", "medicine", "healthy diet", "sleep schedule", "nutrition"],
    "Meditation": ["meditation", "mindfulness", "breathing exercise", "guided meditation", "relaxation"],
    "Study": ["study session", "revise exam", "coursework", "lecture notes", "research paper"],
    "Languages": ["learn language", "vocabulary practice", "speaking practice", "grammar exercises", "language lesson"],
    "Skills": ["learn python", "coding practice", "data analysis", "machine learning", "presentation skills"],
    "Job Search": ["apply for jobs", "update CV", "resume", "cover letter", "linkedin profile"],
    "Interviews": ["interview prep", "mock interview", "technical interview", "behavioral interview"],
    "Work": ["team meeting", "client call", "project deadline", "send email", "weekly report"],
    "Freelance": ["freelance project", "client proposal", "invoice client", "contract work"],
    "Reading": ["read book", "finish chapter", "library", "book notes"],
    "Journaling": ["write journal", "daily reflection", "gratitude journal", "journal prompts"],
    "Hobbies": ["play guitar", "photography", "painting", "gaming", "cooking for fun"],
    "Goals": ["set goals", "goal planning", "monthly goals", "milestones"],
    "Habits": ["habit tracking", "morning routine", "daily habit", "habit streak"],
    "Projects": ["build an app", "side project", "ship feature", "project roadmap"],
}

# -----------------------------
# Text -> vector helpers
# -----------------------------
_word_re = re.compile(r"[a-zA-Z][a-zA-Z']+")

def tokenize(text: str) -> List[str]:
    return _word_re.findall(text.lower())

def text_to_vec(text: str, kv) -> Optional[np.ndarray]:
    toks = tokenize(text)
    vecs = [kv[t] for t in toks if t in kv]
    if not vecs:
        return None
    return np.mean(np.vstack(vecs), axis=0).astype(np.float32)

def build_category_proto(cat: str, seeds: List[str], kv) -> Optional[np.ndarray]:
    seed_vecs = [text_to_vec(s, kv) for s in seeds]
    seed_vecs = [v for v in seed_vecs if v is not None]
    if not seed_vecs:
        return None
    return np.mean(np.vstack(seed_vecs), axis=0).astype(np.float32)

def main():
    out_dir = "protos"
    os.makedirs(out_dir, exist_ok=True)

    # Load pretrained FastText vectors (cached after first download)
    # Good balance: semantic + broad coverage
    model_name = "fasttext-wiki-news-subwords-300"
    kv = api.load(model_name)

    # Safety check: ensure seeds exist for all category names
    cat_names = [c["name"] for c in global_categories]
    missing = sorted(set(cat_names) - set(CATEGORY_SEEDS.keys()))
    if missing:
        raise ValueError(f"Missing CATEGORY_SEEDS entries for: {missing}")

    # Build prototypes
    proto_map: Dict[str, np.ndarray] = {}
    for cat in cat_names:
        proto = build_category_proto(cat, CATEGORY_SEEDS[cat], kv)
        if proto is None:
            raise RuntimeError(f"Could not build vector for category '{cat}' (no tokens in vocab).")
        proto_map[cat] = proto

    # Save vectors to NPZ (fast to load)
    npz_path = os.path.join(out_dir, "prototypes.npz")
    np.savez_compressed(npz_path, **proto_map)

    # Save metadata (colors, model name, seeds)
    meta = {
        "embedding_model": model_name,
        "vector_dim": int(next(iter(proto_map.values())).shape[0]),
        "categories": global_categories,
        "seeds": CATEGORY_SEEDS,
    }
    meta_path = os.path.join(out_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"Saved prototypes to: {npz_path}")
    print(f"Saved metadata to:   {meta_path}")

if __name__ == "__main__":
    main()

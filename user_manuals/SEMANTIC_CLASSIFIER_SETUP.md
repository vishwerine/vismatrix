# Semantic Classification Setup Guide

## Overview

The semantic classification system uses pretrained FastText embeddings to automatically categorize calendar events and activities into global categories (Fitness, Health, Study, Work, etc.).

## Architecture

- **Location**: `tracker/services/semantic_classifier.py` 
- **Loading**: Prototypes and embeddings are loaded **once at process startup** (not on-demand)
- **Storage**: `progress_tracker/protos/` directory
  - `prototypes.npz` - Category prototype vectors
  - `meta.json` - Category metadata and seed phrases

## Setup Instructions

### 1. Install Required Dependencies

```bash
pip install gensim numpy
```

### 2. Build Category Prototypes

Run the Django management command to generate prototypes:

```bash
cd progress_tracker
python manage.py build_prototypes
```

This will:
- Download the FastText model (first run only, ~900MB cached)
- Generate prototype vectors for all global categories
- Save files to `progress_tracker/protos/`

**First run may take 5-10 minutes** as it downloads the embedding model.

### 3. Verify Setup

Check that paths are configured correctly:

```bash
python manage.py test_proto_paths
```

Expected output:
```
✅ PATHS MATCH! All components use the same location.
✅ /path/to/progress_tracker/protos/prototypes.npz exists
✅ /path/to/progress_tracker/protos/meta.json exists
```

### 4. Test Classification

Test the classifier with sample events:

```bash
python manage.py test_script
```

Or test iCloud calendar integration:

```bash
python manage.py test_icloud_classification
```

## Usage in Code

```python
from tracker.services.semantic_classifier import classify_text, MODEL_AVAILABLE

# Check if model is loaded
if MODEL_AVAILABLE:
    category, top_scores = classify_text("gym workout and cardio")
    print(f"Category: {category}")
    # Category: Fitness
    
    for cat, score in top_scores:
        print(f"  {cat}: {score:.3f}")
else:
    print("Semantic classifier not available")
```

## How It Works

1. **At Process Startup**: When Django starts, the module loads quickly:
   - Checks if prototype files exist (fast)
   - Does **NOT** load the model yet (lazy loading)
   - Server starts in seconds, not minutes

2. **On First Use**: When classification is first called:
   - Loads category prototypes from `prototypes.npz`
   - Loads FastText embedding model (takes ~30-180s first time)
   - Model stays in memory for subsequent calls

3. **Subsequent Calls**: Classification is fast (<1ms) because model is cached in memory

4. **Graceful Degradation**: If prototypes aren't available:
   - `MODEL_AVAILABLE = False`
   - `classify_text()` returns "Uncategorized"
   - No errors or crashes

## Customizing Categories

To add/modify categories, edit `build_prototypes.py`:

1. Update `global_categories` list
2. Add seed phrases to `CATEGORY_SEEDS` dictionary
3. Re-run `python manage.py build_prototypes`

## Performance Notes

- **Import time**: <2 seconds (no model loading)
- **First classification**: 30-180 seconds (loads model)
- **Subsequent calls**: <1ms per classification (model cached)
- **Memory usage**: ~1GB for FastText model
- **Thread-safe**: Yes, models loaded once per process
- **Production**: Works with gunicorn/uwsgi (no worker timeout issues)

## Troubleshooting

### "Semantic classifier metadata not found"
- Run `python manage.py build_prototypes` first
- Check that `progress_tracker/protos/` directory exists

### "Import gensim could not be resolved"  
- Install: `pip install gensim numpy`

### Server starts slowly
- **This is NOT expected anymore** - server should start quickly
- Model loads lazily on first classification request
- First request will be slower (~30-180s), subsequent requests are fast

### First classification is slow
- This is expected behavior (lazy loading)
- Model loads on first use (~30-180 seconds)
- Subsequent classifications are fast (<1ms)
- Model stays loaded for the lifetime of the worker process

### Classification returns "Uncategorized"
- Check similarity threshold (default: 0.25)
- Add more seed phrases for that category
- Rebuild prototypes after changes

## Files

- `tracker/services/semantic_classifier.py` - Main classifier (loads at import)
- `tracker/management/commands/build_prototypes.py` - Builds prototypes
- `tracker/management/commands/test_proto_paths.py` - Verify paths
- `tracker/management/commands/test_script.py` - Test classifications
- `progress_tracker/protos/` - Generated prototype files (gitignored)

## Migration from Old Location

If you have code importing from the old location:

```python
# Old (deprecated)
from tracker.management.commands.semantic_classifier import classify_text

# New
from tracker.services.semantic_classifier import classify_text
```

The old location still works with a deprecation warning but will be removed in future versions.

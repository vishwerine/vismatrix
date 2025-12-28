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

1. **At Process Startup**: When Django starts, `semantic_classifier.py` loads:
   - Category prototype vectors from `prototypes.npz`
   - Metadata from `meta.json`
   - FastText embedding model (cached)

2. **At Runtime**: Classification is fast because models are pre-loaded:
   - Converts text to embedding vector
   - Compares with all category prototypes using cosine similarity
   - Returns best match if similarity > threshold

3. **Graceful Degradation**: If prototypes aren't available:
   - `MODEL_AVAILABLE = False`
   - `classify_text()` returns "Uncategorized"
   - No errors or crashes

## Customizing Categories

To add/modify categories, edit `build_prototypes.py`:

1. Update `global_categories` list
2. Add seed phrases to `CATEGORY_SEEDS` dictionary
3. Re-run `python manage.py build_prototypes`

## Performance Notes

- **First import**: ~2-5 seconds (loads model into memory)
- **Subsequent calls**: <1ms per classification
- **Memory usage**: ~1GB for FastText model
- **Thread-safe**: Yes, models loaded once at module level

## Troubleshooting

### "Semantic classifier metadata not found"
- Run `python manage.py build_prototypes` first
- Check that `progress_tracker/protos/` directory exists

### "Import gensim could not be resolved"  
- Install: `pip install gensim numpy`

### Server starts slowly
- This is expected on first startup after restart
- Models load once during Django initialization
- Subsequent requests are fast

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

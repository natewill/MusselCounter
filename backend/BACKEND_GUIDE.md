# Backend Guide - Mussel Counter

This guide explains how the current backend is organized and how data flows through it.

## Architecture Overview

The backend is a FastAPI app with SQLite storage and PyTorch inference:

- FastAPI handles HTTP endpoints
- SQLite stores collections, images, runs, and detections
- PyTorch runs model inference (FASTRCNN or YOLO)
- Uploaded image files are stored on disk (`data/uploads/`)

High-level flow:

```text
Frontend (Next.js)
  -> FastAPI routers
  -> SQLite (metadata/results)
  -> PyTorch model inference
  -> SQLite updates
```

## Core Concepts

### Collection
A named group of images to process together.

### Model
A trained weights file with a canonical type:
- `FASTRCNN`
- `YOLO`

### Run
A model execution on a collection at a threshold.

Run identity is reused by:
- `collection_id`
- `model_id`
- `threshold` (with small float tolerance)

### Detection
Per-object row stored in `detection`:
- `confidence`
- `class` (`live`, `dead`, `edit_live`, `edit_dead`)
- `bbox` JSON string (`[x1,y1,x2,y2]`)

### Image Result
Per-image aggregate row in `image_result` for a run:
- `live_mussel_count`
- `dead_mussel_count`
- `processed_at`
- `error_msg`

## Request Flow (Upload -> Run -> Results)

1. Upload images: `POST /api/collections/{collection_id}/upload-images`
2. Files are validated in `utils/file_processing.py`
3. Dedup is by MD5 hash (`image.file_hash` UNIQUE)
4. Image rows + `collection_image` links are created in `utils/image_utils.py`
5. Start run: `POST /api/collections/{collection_id}/run`
6. `run_utils/db.py` creates/reuses run by `(collection_id, model_id, threshold)`
7. Background task calls `process_collection_run(...)`
8. Model is loaded in a worker thread (`asyncio.to_thread(load_model, ...)`)
9. Images are processed sequentially (one at a time)
10. Detections are stored in `detection`; counts are stored in `image_result`
11. Run totals/status are finalized in `run`

## Inference Behavior

### Model routing
`utils/model_utils/inference/router.py` routes by model type:
- `FASTRCNN` -> `rcnn.py`
- `YOLO` -> `yolo.py`

Both adapters return the same internal dict:

```python
{
  "live_count": int,
  "dead_count": int,
  "polygons": [
    {"confidence": float, "class": "live|dead", "bbox": [x1,y1,x2,y2]}
  ]
}
```

### Threshold handling
Inference stores all detections first. Threshold is applied when counting via SQL logic:

- `edit_live` and `edit_dead` always count
- `live`/`dead` count only if `confidence >= threshold`

Shared count helpers live in `utils/detection_counts.py`.

## Current Run Processing (Important)

Run orchestration is in `utils/run_utils/collection_processor.py`:

- Loads run/model metadata
- Validates weights path exists
- Loads model in background thread
- Builds image worklist by skipping image_ids already in `image_result` for that run
- Processes remaining images sequentially
- Updates `run.processed_count` after each image
- Finalizes status:
  - `completed` if all processed images succeeded
  - `completed_with_errors` if any processed image failed

If all images were already processed for a reused run, it marks the run `completed` and recalculates totals.

## File/DB Cleanup Behavior

When deleting collections or removing images from a collection:

- link rows are removed from `collection_image`
- related `run`/`image_result`/`detection` rows are cleaned up as needed
- orphan images (no remaining collection links) are removed from DB
- orphan upload files are deleted from disk

There is no polygon JSON directory in the current backend flow.

## Important Tables (Current)

From `schema.sql`:

- `collection(collection_id, name, created_at)`
- `image(image_id, filename, stored_path, file_hash)`
- `collection_image(collection_id, image_id, added_at)`
- `model(model_id, name, type, weights_path)`
- `run(run_id, collection_id, model_id, started_at, finished_at, status, error_msg, threshold, total_images, processed_count, live_mussel_count)`
- `image_result(run_id, image_id, live_mussel_count, dead_mussel_count, processed_at, error_msg)`
- `detection(detection_id, run_id, image_id, confidence, class, bbox)`

## Key Backend Files

- `main.py`: app setup, router registration, static upload mount
- `db.py`: DB init + model seeding from `data/models`
- `api/routers/collections.py`: collection CRUD, upload, threshold recalc, image deletion from collection
- `api/routers/runs.py`: start/stop run and fetch run status
- `api/routers/images.py`: image detail + manual class edits
- `utils/run_utils/collection_processor.py`: run orchestration
- `utils/run_utils/image_processor.py`: per-image processing and error recording
- `utils/model_utils/loader.py`: model loading for `FASTRCNN` and `YOLO`
- `utils/model_utils/inference/*`: inference adapters/router
- `utils/detection_counts.py`: shared SQL count logic

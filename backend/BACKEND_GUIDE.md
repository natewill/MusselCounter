# Backend Guide - Understanding the Mussel Counter Backend

This guide explains how the backend works at a high level, so you can understand what's happening without needing to know all the implementation details.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [How a Request Flows Through the System](#request-flow)
3. [Key Concepts](#key-concepts)
4. [File Structure](#file-structure)
5. [How Inference Works](#how-inference-works)
6. [Database Schema](#database-schema)

---

## Architecture Overview

The backend is built with **FastAPI** (a Python web framework) and uses:
- **SQLite** for data storage
- **PyTorch** for running ML models
- **Async/await** for handling multiple requests at once

```
Frontend (Next.js) 
    ↓ HTTP Requests
Backend (FastAPI)
    ↓ Reads/Writes
Database (SQLite)
    ↓ Loads
ML Models (PyTorch)
    ↓ Processes
Images (stored in data/uploads/)
```

---

## Request Flow

### Example: User Uploads Images and Starts a Run

```
1. Frontend sends POST /api/collections/{id}/upload-images
   ↓
2. API Router (collections.py) receives request
   ↓
3. File Validation (file_processing.py)
   - Check file type (is it an image?)
   - Check file size (not too big?)
   - Calculate MD5 hash (for deduplication)
   ↓
4. Save to Database (image_utils.py)
   - Check if hash already exists (deduplication)
   - Save image to data/uploads/
   - Create database record
   ↓
5. Return response with image IDs
   
   
6. Frontend sends POST /api/runs/start
   ↓
7. API Router (runs.py) receives request
   ↓
8. Create/Reuse Run (run_utils/db.py)
   - Check if run with same (collection_id, model_id, threshold) exists
   - If exists: reset to 'pending', reuse it
   - If not: create new run
   ↓
9. Start Background Task (collection_processor.py)
   - Load ML model
   - Get all images
   - Process images in batches
   - Save results to database
   ↓
10. Return run_id immediately (frontend can poll for progress)
```

---

## Key Concepts

### 1. **Collections**
- A "folder" of images that you want to analyze together
- Example: "Beach Survey 2024" with 50 mussel photos

### 2. **Models**
- The AI that detects mussels in images
- Stored in `data/models/` (`.pt` or `.pth` files)
- Two main types:
  - **Faster R-CNN**: Slower but more accurate
  - **YOLO**: Faster but may be less accurate

### 3. **Runs**
- One execution of a model on a collection
- Identified by `(collection_id, model_id, threshold)`
- Example: "Run YOLOv8n at 0.5 threshold on Beach Survey 2024"

### 4. **Threshold**
- Confidence level for detections (0.0 to 1.0)
- 0.5 = "50% sure this is a mussel"
- Higher threshold = fewer but more confident detections
- Lower threshold = more detections but some may be wrong

### 5. **Batch Processing**
- Process multiple images at once (faster than one-by-one)
- Batch size depends on:
  - Model size (larger models = smaller batches)
  - Available memory (GPU has more than CPU)
- Example: YOLOv8n on CPU = batch size 4 (process 4 images at once)

### 6. **Deduplication**
- Same image uploaded twice only stores one copy
- Uses MD5 hash to detect duplicates
- Saves disk space and prevents duplicate processing

---

## File Structure

```
backend/
├── main.py                 # Entry point - sets up FastAPI app
├── config.py              # Configuration (file paths, limits)
├── db.py                  # Database connection and initialization
├── schema.sql             # Database table definitions
│
├── api/
│   ├── routers/           # API endpoints
│   │   ├── collections.py # Collection management
│   │   ├── models.py      # Model information
│   │   ├── runs.py        # Start/stop inference runs
│   │   ├── images.py      # Image detail results
│   │   └── system.py      # Health check
│   ├── schemas.py         # Request/response models (validation)
│   └── error_handlers.py  # Error response formatting
│
├── utils/
│   ├── model_utils/       # ML model handling
│   │   ├── loader.py      # Load models from files
│   │   └── inference.py   # Run models on images
│   │
│   ├── run_utils/         # Inference run orchestration
│   │   ├── collection_processor.py  # Main run coordinator
│   │   ├── image_processor.py       # Process single images
│   │   └── db.py                    # Run database operations
│   │
│   ├── collection_utils.py  # Collection database operations
│   ├── image_utils.py        # Image database operations
│   ├── file_processing.py    # File validation and saving
│   └── validation.py         # Input validation
│
└── data/
    ├── models/            # ML model weight files (.pt, .pth)
    ├── uploads/           # Uploaded images
    └── polygons/          # Detection results (bounding boxes)
```

---

## How Inference Works

### Step-by-Step Process

```
1. User clicks "Start Run" in frontend
   - Selects model (e.g., "YOLOv8n")
   - Sets threshold (e.g., 0.5)

2. Backend creates/reuses run
   - Checks if (collection_id, model_id, threshold) already exists
   - If yes: reuse existing run (only process new images)
   - If no: create new run

3. Model loading (happens in background thread)
   - Load model weights from data/models/
   - Move model to GPU (if available) or CPU
   - Apply optimizations (disable gradients, tune threading)
   - Calculate optimal batch size based on model parameter count

4. Get images to process
   - Fetch all images in collection
   - Check which are already processed for this run
   - Only process the unprocessed ones

5. Batch processing loop
   - Split images into batches (e.g., 4 images per batch)
   - For each batch:
     a. Load images from disk
     b. Run model inference (detect mussels)
     c. Get bounding boxes with labels (live/dead) and confidence
     d. Save polygon data to data/polygons/{image_id}.json
     e. Update database with counts
     f. Update progress counter
   
6. Aggregate results
   - Sum up all live/dead counts
   - Update run status to 'completed'
   - Return final totals

7. Frontend polls and sees updated results
   - Shows green flash animation on processed images
   - Updates collection totals
```

### What the Model Actually Does

```python
# Input: Image file (e.g., mussel_photo.jpg)
image = load_image("mussel_photo.jpg")  # 1920x1080 pixels

# Model processes it
results = model.detect(image, threshold=0.5)

# Output: List of detections
[
    {
        "label": "live",
        "confidence": 0.95,
        "box": [100, 200, 150, 250]  # x1, y1, x2, y2
    },
    {
        "label": "dead",
        "confidence": 0.87,
        "box": [300, 400, 350, 450]
    },
    ...
]

# Then we:
# 1. Filter by confidence (keep >= threshold)
# 2. Count live vs dead
# 3. Convert boxes to polygons (4 corners)
# 4. Save to database
```

---

## Database Schema

### Core Tables

**collection**
```
- collection_id (primary key)
- name ("Beach Survey 2024")
- description (optional)
- created_at
- updated_at
```

**image**
```
- image_id (primary key)
- filename ("mussel1.jpg")
- stored_path ("data/uploads/abc123_mussel1.jpg")
- file_hash (MD5 for deduplication)
- width, height (image dimensions)
- created_at
```

**collection_image** (links images to collections)
```
- collection_id
- image_id
- added_at
```

**model**
```
- model_id (primary key)
- name ("YOLOv8n")
- type ("YOLO")
- weights_path ("data/models/yolov8n.pt")
- description
```

**run**
```
- run_id (primary key)
- collection_id
- model_id
- threshold (0.5)
- status ('pending', 'running', 'completed', 'failed', 'cancelled')
- total_images
- processed_count (for progress tracking)
- live_mussel_count (aggregated)
- dead_mussel_count (aggregated)
- started_at
- finished_at
- error_msg (if failed)
```

**image_result** (results for each image in each run)
```
- run_id + image_id (composite primary key)
- live_mussel_count
- dead_mussel_count
- polygon_path ("data/polygons/123.json")
- processed_at
- error_msg (if failed)
```

### Smart Run Reuse

The system is smart about reusing runs:

```sql
-- Check if run already exists
SELECT * FROM run 
WHERE collection_id = 5 
  AND model_id = 2 
  AND ABS(threshold - 0.5) < 0.001

-- If found: Reset it to 'pending' and reuse
UPDATE run SET status = 'pending' WHERE run_id = 42

-- If not found: Create new run
INSERT INTO run (collection_id, model_id, threshold, ...) VALUES (...)
```

This means:
- Same model + same threshold = reuse run
- Only process images that haven't been processed yet
- Change model or threshold = new run

---

## Performance Optimizations

### Fixed CPU Defaults
CPU threading and batch sizing are now fixed for single-machine use:
- Threads: torch uses 2 threads and 1 interop thread (set in loaders/startup).
- Batch sizes: R-CNN loads with batch_size=1; YOLO loads with batch_size=2.
This keeps behavior consistent without dynamic detection.

### 3. Inference Optimizations
**File**: `utils/model_utils/loader.py`

**Optimizations applied**:
- `torch.set_grad_enabled(False)` - Don't track gradients (only needed for training)
- `model.eval()` - Disable dropout and batch norm training mode
- `torch.backends.cudnn.enabled = False` on CPU - Remove CUDA overhead

### 4. Non-blocking Model Loading
**File**: `utils/run_utils/collection_processor.py`

**Problem**: Loading model blocks the event loop (UI freezes)

**Solution**: Run in background thread
```python
model = await asyncio.to_thread(load_model, weights_path, model_type)
```

### 5. Async File I/O
**File**: `utils/image_utils.py`, `utils/file_processing.py`

**Problem**: Reading/writing files blocks other requests

**Solution**: Use `aiofiles` for non-blocking I/O
```python
async with aiofiles.open(file_path, 'rb') as f:
    content = await f.read()
```

---

## Common Questions

### Why use async/await?
- Allows handling multiple requests at once
- File I/O doesn't block model inference
- API responds quickly even when processing images

### Why process in batches?
- ML models are faster with multiple images at once
- GPU especially benefits from batching
- But too large → out of memory

### Why store polygons separately?
- Keeps database small
- JSON format easy to parse
- Can regenerate from bounding boxes if needed

### How does deduplication work?
- Calculate MD5 hash of file contents
- Check if hash exists in database
- If yes: link existing image to collection
- If no: save new image file

### What if inference fails?
- Error caught and logged
- Run status set to 'failed'
- Error message stored in database
- Partial results kept (images processed before failure)

---

## Troubleshooting

### "Out of Memory" errors
- Model too large for available RAM
- **Solution**: Reduce batch size in `collection_processor.py::MANUAL_BATCH_SIZE = 1`

### Slow inference
- CPU not optimized properly
- **Check**: Logs should show thread optimization
- **Solution**: Verify `pick_threads()` is called on startup

### Images not appearing
- Check file permissions on `data/uploads/`
- Verify static file serving in `main.py` (`app.mount("/uploads", ...)`)
- Check image paths in database match actual files

### Run stuck in 'running'
- Backend crashed during inference
- **Solution**: Manually update database: `UPDATE run SET status = 'failed' WHERE run_id = X`

---

## For Developers

### Adding a New Model Type

1. Add loader in `utils/model_utils/loader.py`:
```python
def load_my_model(weights_path: str, model_type: str):
    model = MyModel()
    model.load_weights(weights_path)
    batch_size = calculate_batch_size_from_model(model, device)
    return model, device, batch_size
```

2. Add inference in `utils/model_utils/inference.py`:
```python
def run_my_model_inference(model_device, image_paths, threshold):
    # Run model on images
    # Return list of results
    pass
```

3. Update `load_model()` dispatcher

### Adding a New API Endpoint

1. Create router in `api/routers/my_router.py`
2. Define request/response models in `api/schemas.py`
3. Register router in `main.py`: `app.include_router(my_router.router)`
4. Test at `http://127.0.0.1:8000/docs`

### Running Tests
```bash
cd backend
pytest  # Run all tests
pytest -v  # Verbose output
pytest tests/test_specific.py  # Run specific test file
```

---

## Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **PyTorch Docs**: https://pytorch.org/docs/
- **Resource Detection Details**: See `RESOURCE_DETECTION.md`
- **API Documentation**: Run backend and visit `http://127.0.0.1:8000/docs`

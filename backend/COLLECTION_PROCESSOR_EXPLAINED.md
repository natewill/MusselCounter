# Collection Processor Explained

**File**: `utils/run_utils/collection_processor.py`

This is the "brain" of the inference system. It coordinates everything needed to run a model on a collection of images. This file is complex, so here's a breakdown of how it works.

## What This File Does

Takes a `run_id` and:
1. Loads the ML model from disk
2. Gets all images in the collection
3. Figures out which images still need processing
4. Processes images in batches (for speed)
5. Saves results to database as they complete
6. Updates progress in real-time
7. Handles errors gracefully

## Key Functions

### `process_collection_run(db, run_id)`
**The main orchestrator - coordinates the entire inference run**

```python
# Simplified flow:
1. Get run info from database (which model? which collection? what threshold?)
2. Update status to 'running'
3. Load the ML model (happens in background thread so UI doesn't freeze)
4. Get all images in the collection
5. Check which images are already processed for this run
6. Only process the unprocessed ones
7. Split images into batches (e.g., 4 images per batch)
8. Process each batch:
   - Run model inference
   - Save polygon data to JSON files
   - Update database with counts
   - Update progress counter
9. Calculate final totals
10. Update run status to 'completed'
```

### Why Batch Processing?

**Problem**: Processing one image at a time is slow
```python
# Slow way (one at a time):
for image in images:  # 100 images
    result = model.run(image)  # Takes 2 seconds each
# Total: 200 seconds
```

**Solution**: Process multiple images at once
```python
# Fast way (batches of 4):
for batch in split_into_batches(images, size=4):  # 25 batches
    results = model.run(batch)  # Takes 3 seconds per batch
# Total: 75 seconds (2.6x faster!)
```

### Smart Run Reuse

The system is smart about not reprocessing images:

```python
# Example scenario:
Collection: "Beach Survey" with 10 images
Run 1: YOLOv8n at 0.5 threshold
  - Processes all 10 images
  - Saves results

User uploads 5 more images (total: 15)

Run 2: Same YOLOv8n at 0.5 threshold
  - Reuses Run 1 (same model + threshold)
  - Only processes the 5 new images
  - Keeps results from first 10 images
  - Updates totals to include all 15
```

## Complex Sections Explained

### 1. Model Loading in Background Thread

**Why**: Loading a model can take 100-500ms and blocks everything

**Problem**:
```python
# This blocks the entire server
model = load_model(weights_path)  # UI freezes for 500ms!
```

**Solution**:
```python
# Run in background thread - server stays responsive
model = await asyncio.to_thread(load_model, weights_path)
```

### 2. Batch Processing Loop

```python
# Split images into batches
image_batches = [images[i:i + batch_size] for i in range(0, len(images), batch_size)]
# Example: 10 images, batch_size=4 → [[0-3], [4-7], [8-9]]

# Process batches concurrently (with limits)
for batch in asyncio.as_completed(tasks):
    results = await batch  # Get results as they finish
    # Save to database immediately
    # Update progress counter
```

**Key Points**:
- `asyncio.as_completed()` - Get results as they finish (not in order)
- `Semaphore` - Limit concurrent batches (prevents memory explosion)
- Real-time updates - Database updated after each batch completes

### 3. Polygon Data Saving

```python
# For each detected mussel:
polygon_data = {
    'polygons': [
        {
            'coords': [[x1,y1], [x2,y1], [x2,y2], [x1,y2]],
            'confidence': 0.95,
            'class': 'live'
        },
        # ... more detections
    ],
    'live_count': 5,
    'dead_count': 2,
    'threshold': 0.5,
    'image_width': 1920,
    'image_height': 1080
}

# Save to: data/polygons/{image_id}.json
```

### 4. Database Updates

**Two types of updates**:

**1. Immediate batch updates** (after each batch completes):
```python
# Update image dimensions
UPDATE image SET width = ?, height = ? WHERE image_id = ?

# Save detection results
INSERT INTO image_result (run_id, image_id, live_count, dead_count, ...)
VALUES (?, ?, ?, ?, ...)

# Update progress
UPDATE run SET processed_count = ? WHERE run_id = ?
```

**2. Final aggregation** (when run completes):
```python
# Sum up all counts
total_live = SUM(live_mussel_count)
total_dead = SUM(dead_mussel_count)

# Update run totals
UPDATE run 
SET live_mussel_count = ?, dead_mussel_count = ?, status = 'completed'
WHERE run_id = ?
```

## Error Handling

The system handles many types of errors:

### Model Loading Fails
```python
try:
    model = await load_model(weights_path)
except Exception as e:
    await _fail(db, run_id, f"Failed to load model: {e}")
    return  # Stop processing
```

### Image File Missing
```python
if not Path(image_path).exists():
    # Record error for this image but continue with others
    await db.execute(
        "INSERT INTO image_result (..., error_msg) VALUES (..., ?)",
        (f"Image file not found: {image_path}",)
    )
```

### Inference Crashes
```python
try:
    results = await _batch_infer(model, images, threshold)
except Exception as e:
    # Mark run as failed
    await _fail(db, run_id, f"Inference error: {e}")
```

## Performance Optimizations

### 1. Concurrent Batch Processing
```python
# Process multiple batches at once (up to limit)
max_concurrent_batches = 1  # Usually 1 to avoid memory issues
semaphore = asyncio.Semaphore(max_concurrent_batches)

async def process_batch(batch):
    async with semaphore:  # Wait if limit reached
        return await _batch_infer(model, batch, threshold)
```

### 2. Incremental Database Writes
```python
# Don't wait until end - write results as we go
for batch_result in as_completed(tasks):
    # Immediately save this batch's results
    await db.executemany("INSERT INTO image_result ...", batch_result)
    await db.commit()
    
    # Frontend can see progress in real-time!
```

### 3. Smart Image Filtering
```python
# Don't process what's already done
already_processed_ids = set(
    await db.execute(
        "SELECT image_id FROM image_result WHERE run_id = ?",
        (run_id,)
    )
)

images_to_process = [
    img for img in all_images 
    if img['image_id'] not in already_processed_ids
]
```

## Common Scenarios

### Scenario 1: First Run on Collection
```
Collection: 50 images
Run: YOLOv8n, threshold 0.5

Flow:
1. Load YOLOv8n model
2. Get all 50 images
3. Check for existing results → none found
4. Split into batches: 50 / 4 = 13 batches (12 full + 1 partial)
5. Process batch 1 (4 images):
   - Run inference
   - Get 15 live, 3 dead
   - Save polygons to 4 JSON files
   - Update database
   - processed_count = 4
6. Process batch 2...
7. ...continue until all batches done
8. Sum totals: 180 live, 42 dead
9. Mark run complete
```

### Scenario 2: Adding Images to Existing Run
```
Collection: 50 images (all processed)
User adds: 10 more images (total: 60)
Run: Same YOLOv8n, same 0.5 threshold

Flow:
1. Check for existing run with (collection_id, model_id, threshold)
2. Found! Run ID 42
3. Reset Run 42 status to 'pending'
4. Load model
5. Get all 60 images
6. Check existing results → 50 already done
7. Only process 10 new images (3 batches)
8. Recalculate totals from ALL 60 images
9. Update run with new totals
10. Mark complete
```

### Scenario 3: Changing Threshold
```
Collection: 50 images
Previous run: YOLOv8n at 0.5 (Run ID 42)
New run: YOLOv8n at 0.7

Flow:
1. Check for existing run with (collection_id, model_id, 0.7)
2. Not found! Different threshold
3. Create new run (Run ID 43)
4. Process all 50 images again
   - Higher threshold = fewer detections
   - Different results than Run 42
5. Both runs exist in database
6. User can compare: "0.5 found 180, but 0.7 found 120"
```

## Manual Overrides

For debugging or special cases:

```python
# Top of collection_processor.py:
MANUAL_BATCH_SIZE = None  # Set to force batch size (e.g., 2)
MANUAL_MAX_CONCURRENT_BATCHES = None  # Set to limit concurrency (e.g., 1)

# Example: Computer struggling with default batch size
MANUAL_BATCH_SIZE = 1  # Process one image at a time
```

## Logging

The system logs everything important:

```python
logger.info(f"[RUN {run_id}] Starting collection processing")
logger.debug(f"[RUN {run_id}] Using batch_size={batch_size}")
logger.error(f"[RUN {run_id}] Failed to load model: {error}")
```

**Tip**: Set `UVICORN_LOG_LEVEL=debug` to see detailed logs

## Summary

The collection processor is complex because it handles:
- ✅ Concurrent processing (multiple batches at once)
- ✅ Real-time progress updates
- ✅ Smart run reuse
- ✅ Error handling at multiple levels
- ✅ Memory management (batch size, concurrent limits)
- ✅ Database atomicity (consistent state even if crashes)

But at its core, it's just:
1. Load model
2. Get images
3. Process in batches
4. Save results
5. Update totals

Everything else is optimization and error handling!


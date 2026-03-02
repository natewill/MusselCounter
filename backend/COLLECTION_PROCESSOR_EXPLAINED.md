# Collection Processor Explained

**File:** `utils/run_utils/collection_processor.py`

This module is the run orchestrator. It controls model loading, image work selection, per-image processing, progress updates, and final run status.

## What It Does

Given a `run_id`, it:

1. Loads run metadata from `run`
2. Resolves model metadata from `model`
3. Loads model weights (in a worker thread)
4. Finds collection images and skips already-processed ones
5. Processes remaining images sequentially
6. Updates progress after each image
7. Finalizes run totals/status

## Current Design Choices

### Sequential processing (no batch pipeline)
Images are processed one-by-one intentionally to reduce CPU spikes and simplify runtime behavior.

### Reusable runs
A run may already exist for the same `(collection_id, model_id, threshold)`. In that case:
- images that already have `image_result` rows for that `run_id` are skipped
- only missing images are processed

### DB-backed progress
After every image, `run.processed_count` is updated so the frontend can poll live progress.

## Main Function

## `process_collection_run(db, run_id)`

High-level flow:

1. `_setup_run_and_load_model(...)`
2. `_prepare_images(...)`
3. Initialize run counters (`total_images`, `processed_count`)
4. `_process_single_images(...)`
5. `_finalize_run(...)`

Error path:
- Any unhandled exception marks the run failed via `_fail(...)`
- Recovery logic checks if no work remains; if true, marks run `completed`

## Helper Functions

### `_setup_run_and_load_model(...)`

- Loads `run` row
- Sets run status to `running`
- Loads `model` row and validates `weights_path`
- Calls `await asyncio.to_thread(load_model, weights_path, model_type)`

Return value:
- `(model_device, collection_id, threshold, model_type)`
- or `None` if setup fails

### `_prepare_images(...)`

- Fetches all collection images via `get_collection_images(...)`
- Reads already-processed image_ids from `image_result` for this `run_id`
- Returns:
  - `images_to_process`
  - `total_images`
  - `images_already_done`

### `_process_single_images(...)`

For each remaining image:

- calls `process_image_for_run(...)`
- appends `(image_id, success, live_count, dead_count)` to results
- updates `run.processed_count`

This function does not do model-specific logic directly.

### `_finalize_run(...)`

- Counts successes from returned tuples
- Sums run live count from `image_result`
- Sets terminal run state:
  - `completed` if all images processed in this invocation succeeded
  - `completed_with_errors` otherwise
- Sets:
  - `finished_at`
  - `total_images`
  - `processed_count`
  - `live_mussel_count`

### `_handle_all_images_processed(...)`

Fast path when there is nothing left to process:
- recomputes run live total from `image_result`
- sets run to `completed`

### `_fail(...)`

Best-effort error updater around `update_run_status(...)`.
Secondary failures while reporting are intentionally suppressed.

## Relationship To `image_processor.py`

`collection_processor.py` delegates actual per-image work to `process_image_for_run(...)`, which handles:

- image file existence checks
- inference call (`run_inference_on_image`)
- storing detection rows in `detection`
- thresholded counting via `utils/detection_counts.py`
- writing/updating `image_result`
- per-image error recording (`error_msg`)

## Status Semantics

Run status values used here:

- `pending`
- `running`
- `completed`
- `completed_with_errors`
- `failed`

`cancelled` exists in schema and can be set by the stop endpoint, but collection processor itself focuses on setup/process/finalize paths above.

## Why `asyncio.to_thread(...)` Is Used

Model loading is CPU/blocking work. Running it in a worker thread keeps the event loop responsive for other API requests.

## Practical Debug Checklist

If a run looks wrong, check in this order:

1. `run.status`, `run.error_msg`, `run.processed_count`, `run.total_images`
2. `model.weights_path` exists on disk
3. `image_result` rows for that `run_id`
4. `detection` rows for that `run_id`
5. per-image `error_msg` in `image_result`

That sequence usually tells you whether failure happened in setup, inference, detection save, or finalize.

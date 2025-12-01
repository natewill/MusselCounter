# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MusselCounter is a full-stack application for automated mussel detection and counting in images using ML models. The system consists of a Python FastAPI backend for ML inference and a Next.js React frontend for user interaction.

**Core Architecture**:
- Backend (Python FastAPI): Handles ML model inference, image processing, and data persistence
- Frontend (Next.js 16 + React 19): Provides UI for image upload, run management, and result visualization
- Database (SQLite): Stores collections, images, models, runs, and detection results
- ML Models: Supports YOLO and Faster R-CNN variants for object detection

## Development Commands

### Backend Setup & Development
```bash
# Initial setup (from backend/)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run development server
cd backend
source venv/bin/activate
uvicorn main:app --reload

# Access backend
# API: http://127.0.0.1:8000
# API Docs: http://127.0.0.1:8000/docs
```

### Frontend Setup & Development
```bash
# Initial setup (from frontend/)
npm install

# Run development server
cd frontend
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Access frontend: http://localhost:3000
```

### Testing
```bash
# Backend tests (when implemented)
cd backend
source venv/bin/activate
pytest                    # Run all tests
pytest --cov             # With coverage

# Frontend tests (when implemented)
cd frontend
npm test                 # Run tests
npm run lint            # Lint code
```

## Key Architecture Concepts

### Backend Architecture

**Separation of Concerns**:
- `main.py`: FastAPI app initialization, middleware, and routing
- `api/routers/`: HTTP endpoint handlers (collections, models, runs, images, system)
- `utils/`: Business logic modules (model loading, inference, file processing)
- `db.py`: Database connection and initialization
- `config.py`: Centralized configuration (paths, limits, CORS)

**Model Loading & Inference Pipeline**:
1. Models auto-discovered from `backend/data/models/` at startup
2. Model type inferred from filename (e.g., "yolo" → YOLO, "rcnn"/"faster" → R-CNN)
3. Optimal batch size calculated based on model parameter count (see `utils/model_utils/loader.py`)
4. Inference runs via `utils/run_utils/collection_processor.py` which orchestrates the entire process
5. Results stored in database and polygon files in `data/polygons/`

**Run Reuse System**:
- Runs are uniquely identified by `(collection_id, model_id, threshold)` tuple
- Starting a run with same parameters reuses existing run and only processes new images
- Enables incremental processing: add images to collection and restart run without reprocessing existing images

**Batch Processing**:
- Images processed in batches for performance (batch size auto-calculated per model)
- CPU thread count set to `cpu_count // 3` to reduce contention
- Progress tracked in real-time via `run.processed_count` field

**Key Utilities**:
- `utils/run_utils/collection_processor.py`: Main inference orchestrator (reads COLLECTION_PROCESSOR_EXPLAINED.md for details)
- `utils/run_utils/image_processor.py`: Batch processing and polygon generation
- `utils/model_utils/loader.py`: Model loading and batch size calculation
- `utils/model_utils/inference.py`: ML inference logic for YOLO and R-CNN
- `utils/file_processing.py`: Upload validation and file handling
- `utils/image_utils.py`: Image deduplication by MD5 hash

### Frontend Architecture

**Data Flow**:
1. API calls centralized in `lib/api.ts` (uses axios with retry logic)
2. Custom hooks manage state and data fetching (TanStack Query for server state)
3. Components receive props from hooks and render UI
4. User interactions trigger hook functions that call API

**Custom Hooks Pattern**:
- `useCollectionData`: Fetches collection details, images, and latest run (polls during active runs)
- `useRunState`: Manages run status and provides cancel/restart functions
- `useStartRun`: Handles starting new inference runs
- `useModels`: Fetches available models
- `useImageUpload`: Manages image upload with progress tracking
- `useImageDelete`: Handles image deletion with optimistic updates
- `useThresholdRecalculation`: Recalculates counts without re-running model

**Component Organization**:
- `components/home/`: Landing page upload and collection creation
- `components/run/`: Run dashboard, image list, controls
- `components/edit/`: Image detail view with polygon overlays and editing

**State Management**:
- Server state via TanStack Query (automatic caching, refetching, optimistic updates)
- URL state for image/collection IDs (Next.js App Router)
- Local state via useState for UI-only state (modals, toggles)

### Database Schema

**Key Tables**:
- `collection`: Groups of images for analysis
- `image`: Unique images (deduplicated by file hash)
- `collection_image`: Many-to-many junction table
- `model`: ML model metadata and optimal batch sizes
- `run`: Inference runs with status tracking
- `image_result`: Per-image results for each run (live/dead counts)
- `detection`: Individual mussel detections with confidence scores (enables threshold recalculation)

**Important Relationships**:
- Collections have many images (many-to-many via `collection_image`)
- Runs belong to one collection and one model
- Image results are unique per `(run_id, image_id)` pair
- Detections store raw model output; image_result stores filtered counts based on threshold

## Common Development Tasks

### Adding a New API Endpoint

1. Define Pydantic schema in `backend/api/schemas.py` (if needed)
2. Add router function in `backend/api/routers/{domain}.py`
3. Implement business logic in `backend/utils/{domain}_utils.py`
4. Add API client function in `frontend/lib/api.ts`
5. Create custom hook in `frontend/hooks/` (if complex state management needed)
6. Use hook in component

### Working with ML Models

- Place model files (`.pt`, `.pth`, `.ckpt`) in `backend/data/models/`
- Models auto-loaded on startup via `main.py:lifespan()` function
- Model type inferred from filename: "yolo" → YOLO, "rcnn"/"faster" → Faster R-CNN
- Batch size auto-calculated in `utils/model_utils/loader.py:calculate_batch_size_from_model()`
- See `RESOURCE_DETECTION.md` for performance tuning details

### Understanding Runs

- Run orchestration happens in `utils/run_utils/collection_processor.py`
- Read `COLLECTION_PROCESSOR_EXPLAINED.md` for detailed explanation of the flow
- Runs execute in background (asyncio) to avoid blocking API responses
- Progress tracked via polling `GET /api/runs/{run_id}` from frontend
- Can be cancelled via `POST /api/runs/{run_id}/stop`

### Threshold Recalculation

- Changing threshold doesn't require re-running model
- Frontend sends `POST /api/runs/{run_id}/recalculate-threshold` with new threshold
- Backend filters existing detections from `detection` table by confidence score
- Updates `image_result` and `run` aggregates instantly
- Much faster than full re-inference

## Important Patterns & Conventions

### File Paths
- Use `Path` objects from `pathlib` for cross-platform compatibility
- Validate paths using `utils/security.py:validate_path()`
- Never hardcode absolute paths; use config constants from `config.py`

### Async Operations
- Backend uses `async/await` throughout (FastAPI is async-native)
- Database operations via `aiosqlite` (async SQLite wrapper)
- File I/O via `aiofiles` for non-blocking reads/writes
- Model inference runs in background thread pool to avoid blocking event loop

### Error Handling
- Backend uses custom exception handlers in `api/error_handlers.py`
- Frontend has ErrorBoundary component wrapping page content
- API client in `lib/api.ts` automatically retries on 429/5xx errors (up to 3 times)

### Image Deduplication
- Images deduplicated by MD5 file hash (calculated during upload)
- Same file uploaded multiple times only stores one copy
- `image.file_hash` column has UNIQUE constraint
- Upload API returns `duplicate_count` and `duplicate_image_ids`

### Security Considerations
- Path traversal protection via `utils/security.py`
- File type validation via magic bytes, not just extensions
- File size limits enforced in `config.py` (50MB images, 1GB models)
- Collection size limit (1000 images max)
- CORS restricted to localhost:3000 in development

## Common Pitfalls & Solutions

**Problem**: Model inference freezes UI
**Solution**: Inference runs in background via `asyncio.create_task()` - never await directly in endpoint handler

**Problem**: Frontend not updating during run
**Solution**: Use polling hook `useCollectionData` with appropriate interval (1-2 seconds during active runs)

**Problem**: Images processing slowly
**Solution**: Check batch size in model table - may need adjustment in `calculate_batch_size_from_model()`

**Problem**: Import errors after adding new dependencies
**Solution**: Backend: ensure venv activated and `pip install -r requirements.txt` ran. Frontend: run `npm install`

**Problem**: Database locked errors
**Solution**: SQLite doesn't handle high concurrency well - ensure using `aiosqlite` and not blocking on long operations

**Problem**: Threshold change not reflecting
**Solution**: Ensure using recalculate endpoint, not starting new run. Check frontend is refetching collection data after recalculation

## Reference Documentation

- `README.md`: Project overview, setup instructions, API documentation
- `backend/BACKEND_GUIDE.md`: Backend architecture deep dive
- `backend/COLLECTION_PROCESSOR_EXPLAINED.md`: Detailed explanation of run orchestration
- `backend/RESOURCE_DETECTION.md`: Performance optimization and batch sizing
- `AGENTS.md`: Repository guidelines for commits, testing, and style (read this for coding conventions)
- API Docs: http://127.0.0.1:8000/docs (auto-generated from FastAPI, available when backend running)

## Tech Stack Details

- **Backend**: Python 3.8+, FastAPI, Uvicorn (ASGI server), aiosqlite, PyTorch, Ultralytics YOLO
- **Frontend**: Next.js 16 (App Router), React 19, TypeScript, TanStack Query, Axios, Tailwind CSS 4
- **Database**: SQLite 3 with async driver (aiosqlite)
- **ML**: PyTorch 2.0+, torchvision, Ultralytics YOLOv5/v8, Faster R-CNN with ResNet50-FPN

## Notes for Future Development

- Automated test suites not yet implemented (manual testing currently used)
- Consider WebSocket for real-time progress updates instead of polling
- GPU support exists but not heavily tested (optimized for CPU by default)
- Model type detection could be improved with better heuristics or metadata file

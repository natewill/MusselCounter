# Mussel Counter Application

A web application for automated detection and counting of live and dead mussels in images using machine learning models (YOLO and Faster R-CNN).

## Setup

### Prerequisites
- **Node.js** (v18+) - Install on macOS: `brew install node`
- **Python** (3.8+)

### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Key Dependencies:**
- `fastapi` - Web framework for building APIs
- `uvicorn` - ASGI server for running FastAPI
- `aiosqlite` - Async SQLite database operations
- `torch` & `torchvision` - PyTorch for ML model inference
- `ultralytics` - YOLO model support
- `pillow` - Image processing
- `aiofiles` - Async file I/O operations

### Add Models
Place your model files in `backend/data/models/` directory. The application automatically detects and loads models on startup.

**Supported file formats:** `.pt`, `.pth`, `.ckpt`

**Supported Model Types:**
- **Faster R-CNN**: ResNet50-FPN backbone (detected from filename containing "rcnn" or "faster")
- **YOLO**: YOLOv5, YOLOv8 variants (detected from filename containing "yolo")

**Auto-Detection:**
- Models are automatically added to the database on first startup
- Model type is inferred from filename
- Batch size is automatically calculated based on model parameter count
- No manual database setup required

**Example:**
```bash
# Place models in the models directory
cp yolov8n.pt backend/data/models/
cp faster_rcnn_resnet50.pth backend/data/models/

# Start the backend - models are auto-loaded
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
```

---

## Running the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Access Points:**
- **Frontend**: http://localhost:3000
- **Backend API**: http://127.0.0.1:8000
- **API Docs**: http://127.0.0.1:8000/docs (auto-generated Swagger UI)
- **Image Uploads**: http://127.0.0.1:8000/uploads/{filename}

---

## File Structure

### Backend (`backend/`)

```
backend/
├── main.py                      # FastAPI app entry point
├── config.py                    # Settings (paths, limits, env)
├── db.py                        # Database connection/init
├── schema.sql                   # SQLite schema
├── requirements.txt             # Python dependencies
├── api/
│   ├── routers/                 # API endpoints (collections, models, runs, images, system)
│   ├── schemas.py               # Pydantic request/response models
│   └── error_handlers.py        # Error formatting
├── utils/
│   ├── model_utils/             # Model loading, inference, DB operations
│   ├── run_utils/               # Run orchestration and processing
│   ├── collection_utils.py      # Collection database operations
│   ├── image_utils.py           # Image DB ops & deduplication
│   ├── file_processing.py       # Upload validation/saving
│   ├── validation.py            # Input validation
│   └── security.py              # Path/security checks
├── data/
│   ├── models/                  # ML model files (.pt, .pth)
│   ├── uploads/                 # Uploaded images
│   └── polygons/                # Detection polygon data (JSON)
├── BACKEND_GUIDE.md             # Backend architecture walkthrough
├── COLLECTION_PROCESSOR_EXPLAINED.md  # Run coordination deep dive
└── RESOURCE_DETECTION.md        # Batch sizing and optimization notes
```

**Architecture Principles**:
- **Separation of Concerns**: API layer separate from business logic
- **Modular Design**: Each utility handles one responsibility
- **Async-First**: All I/O operations use async/await
- **Database Abstraction**: All database operations in dedicated utility files

### Frontend (`frontend/`)

```
frontend/
├── app/                         # Next.js App Router pages
│   ├── layout.tsx               # Root layout + theme
│   ├── globals.css              # Global styles
│   ├── page.tsx                 # Home page (/)
│   ├── collection/[collectionId]/page.tsx   # Collection dashboard
│   └── edit/[imageId]/page.tsx              # Image detail + polygon editor
├── components/                  # Reusable UI components
│   ├── home/                    # Upload, error display
│   ├── run/                     # Run status, controls, image list
│   └── edit/                    # Image display, overlays, edit modals
├── hooks/                       # Custom React hooks for data fetching
├── lib/
│   └── api.ts                   # API client (axios)
├── utils/                       # Helper functions
└── public/                      # Static assets
```

**Architecture Principles**:
- **Component Isolation**: Components focused on single UI responsibilities
- **Custom Hooks**: Business logic separate from rendering
- **API Abstraction**: All backend calls through centralized API client
- **Type Safety**: TypeScript throughout

---

## Tech Stack

### Backend
- **FastAPI** + **Uvicorn** - Modern Python web framework with async support
- **SQLite** - Lightweight, serverless database
- **PyTorch** + **Ultralytics** - ML inference engine
- **aiosqlite** - Async database operations

### Frontend
- **Next.js 16** - React framework with App Router
- **React 19** - UI library
- **TanStack Query** - Server state management
- **Axios** - HTTP client
- **Tailwind CSS 4** - Utility-first styling
- **TypeScript** - Type safety

---

## Key Features

### Smart Run Management
- **Run Reuse**: Runs uniquely identified by `(collection_id, model_id, threshold)` tuple
- **Incremental Processing**: Only new images are processed when restarting a run
- **Real-time Updates**: Image results written to database as batches complete
- **Progress Tracking**: Live progress updates during inference
- **Run Cancellation**: Stop ongoing runs via UI

### Threshold Recalculation
- **Instant Updates**: Change threshold without re-running model
- **Confidence Filtering**: Backend stores all detections with confidence scores
- **On-Demand Calculation**: Counts recalculated from stored detections
- **Visual Filtering**: Edit page only shows detections above current threshold

### Resource Optimization
- **CPU Thread Optimization**: PyTorch threading configured based on CPU cores
- **Dynamic Batch Sizing**: Batch size calculated from model parameter count
- **Non-blocking Operations**: Model loading and inference run in background
- **Inference Optimizations**: Gradient tracking disabled, CUDA disabled on CPU

### Image Management
- **Deduplication**: Images deduplicated by MD5 hash
- **Async File I/O**: Non-blocking file operations with `aiofiles`
- **Visual Feedback**: Color-coded status indicators (orange=unprocessed, green=processing, flash on completion)
- **Smart Sorting**: Recently processed images sort to top

### Model Support
- **Auto-Detection**: Models automatically loaded from `data/models/` on startup
- **Multi-Model Support**: Faster R-CNN and YOLO variants
- **Parameter-Based Batching**: Batch size scales with model size
- **Graceful Fallbacks**: Handles missing models and inference errors

---

## Pages

### Home `/`
- Drag-and-drop or file picker upload
- Quick-process mode: create collection and upload in one step
- Manual mode: create empty collection first

### Collection Dashboard `/collection/[collectionId]`
- View collection totals and all images
- Start/stop runs with model selection
- Adjust threshold with live recalculation
- Upload additional images
- Delete images

### Image Detail `/edit/[imageId]?modelId={modelId}`
- View single image with detection overlays
- Edit polygon classifications (live/dead)
- Toggle overlay visibility
- Fullscreen view
- Only shows detections above current threshold

---

## API Reference

### Collection Endpoints

**`GET /api/collections`**
Get all collections.

**`POST /api/collections`**
Create a new collection.
- Body: `{ name?: string, description?: string }`
- Returns: `{ collection_id: number }`

**`GET /api/collections/{collectionId}`**
Get collection details with images and latest run.
- Optional query param: `?model_id={id}` to filter by specific model
- Returns: Collection metadata, images with results, latest run status

**`POST /api/collections/{collectionId}/upload-images`**
Upload images (multipart/form-data).
- Images deduplicated by hash
- Returns: Added/duplicate counts and image IDs

**`DELETE /api/collections/{collectionId}/images/{imageId}`**
Remove image from collection.

**`GET /api/collections/{collectionId}/recalculate`**
Recalculate counts for new threshold without re-running model.
- Query params: `threshold`, `model_id`

### Model Endpoints

**`GET /api/models`**
Get all available models.

**`GET /api/models/{modelId}`**
Get specific model information.

### Run Endpoints

**`POST /api/collections/{collectionId}/run`**
Start inference run.
- Body: `{ model_id: number, threshold?: number }`
- Returns: Run object with status
- Reuses existing run if same config exists

**`GET /api/runs/{runId}`**
Get run status and results.

**`POST /api/runs/{runId}/stop`**
Cancel running inference.

### Image Endpoints

**`GET /api/images/{imageId}/results`**
Get detailed results for an image.
- Query params: `collection_id`, `model_id`
- Returns: Image metadata, counts, polygons, model info

**`POST /api/images/{imageId}/detections/{detectionId}/classify`**
Update polygon classification.
- Body: `{ new_class: 'live' | 'dead' }`

### Static Files

**`GET /uploads/{filename}`**
Serve uploaded images.

---

## Database Schema

**Core Tables:**
- `collection` - Image collections
- `image` - Unique images (deduplicated by hash)
- `collection_image` - Many-to-many junction table
- `model` - ML models and metadata
- `run` - Inference runs (unique per collection+model+threshold)
- `image_result` - Per-image results for each run
- `detection` - Individual detections with confidence scores

**Key Features:**
- Foreign key constraints for data integrity
- Async operations via `aiosqlite`
- Automatic initialization from `schema.sql`
- Indexes for fast lookups

---

## Performance

### Typical Speeds (CPU)
| Model | Parameters | Batch Size | Speed (10 images) |
|-------|-----------|-----------|-------------------|
| YOLOv8n | 3.2M | 4 | ~8 seconds |
| YOLOv8s | 11.2M | 2 | ~12 seconds |
| Faster R-CNN | 25M | 2 | ~35 seconds |
| YOLOv8x | 68.2M | 1 | ~35 seconds |

**Optimizations:**
- CPU thread count: `cpu_count // 3`
- Gradient tracking disabled
- Batch processing
- Background model loading

---

## Documentation

- **Backend Architecture**: See `backend/BACKEND_GUIDE.md`
- **Run System**: See `backend/COLLECTION_PROCESSOR_EXPLAINED.md`
- **Performance Tuning**: See `backend/RESOURCE_DETECTION.md`
- **Code Guidelines**: See `CLAUDE.md`
- **Interactive API Docs**: http://127.0.0.1:8000/docs (when running)

---

## Development

### Project Structure
- **Backend**: Python 3.8+, FastAPI, async/await throughout
- **Frontend**: Next.js 16 App Router, React 19, TypeScript
- **Database**: SQLite with async driver
- **ML Models**: PyTorch 2.0+, Ultralytics YOLO

### Key Files
- `backend/main.py` - FastAPI app setup
- `backend/schema.sql` - Database schema
- `frontend/lib/api.ts` - API client
- `frontend/hooks/` - Data fetching logic

### Common Tasks
- **Add endpoint**: Create function in `backend/api/routers/`, add utility in `backend/utils/`
- **Add component**: Create in `frontend/components/`, use hooks for data
- **Update schema**: Modify `schema.sql`, delete database to reset

---

## Notes

- Database resets on startup if empty (development mode)
- Images stored in `backend/data/uploads/`
- Detection data stored as JSON in `backend/data/polygons/`
- Frontend polls collection endpoint for real-time updates during runs
- All coordinates stored in original image dimensions, scaled for display

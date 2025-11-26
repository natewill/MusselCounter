# Mussel Counter Application

## Setup

### Prerequisites
- Node.js (v18+), if you don't have node install in mac by running `brew install node`
- Python (3.8+)

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
- `python-dotenv` - Environment variable management

### Add Models
Place your model files in `backend/data/models/` directory. The application automatically detects and loads models on startup.

**Supported file formats:** `.pt`, `.pth`, `.ckpt`

**Supported Model Types:**
The application supports object detection models that output bounding boxes:
- **Faster R-CNN**: ResNet50-FPN backbone (automatically detected from filename)
- **YOLO**: YOLOv5, YOLOv8 variants (nano, small, medium, large, xlarge)
- **SSD**: Single Shot Detector (placeholder, not yet implemented)
- **CNN**: Custom CNN-based detection (placeholder, not yet implemented)

**Auto-Detection:**
- Models are automatically added to the database on first startup
- Model type is inferred from filename (e.g., "yolo" → YOLO, "rcnn"/"faster" → R-CNN)
- Batch size is automatically calculated based on model parameter count and available hardware
- No manual database setup required!

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

## Running

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
- **Backend API**: http://127.0.0.1:8000
- **API Docs**: http://127.0.0.1:8000/docs (auto-generated Swagger UI)
- **Frontend**: http://localhost:3000
- **Image Uploads**: http://127.0.0.1:8000/uploads/{filename} (static file serving)

---

## Testing

Automated test suites are not included in this trimmed-down build. To verify changes manually:
- Start backend (`uvicorn main:app --reload`) and frontend (`npm run dev`) in separate terminals.
- Confirm uploads, model detection, and run workflows on the dashboard and run pages.
- Check API docs at `http://127.0.0.1:8000/docs` for endpoint responses.

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
├── api/                         # API layer
│   ├── routers/                 # collections.py, models.py, runs.py, images.py, system.py
│   ├── schemas.py               # Pydantic models
│   ├── error_handlers.py        # Error formatting
│   └── middleware/              # ASGI middleware init
├── utils/                       # Business logic
│   ├── model_utils/             # Loader/inference/model DB helpers
│   ├── run_utils/               # Run orchestration and DB helpers
│   ├── collection_utils.py      # Collection DB ops
│   ├── image_utils.py           # Image DB ops & dedup
│   ├── file_processing.py       # Upload validation/saving
│   ├── resource_detector.py     # CPU/batch tuning
│   ├── validation.py            # Input validation
│   ├── security.py              # Path/security checks
│   └── logger.py                # Logging setup
├── data/                        # Persistent data (models/uploads/polygons)
├── BACKEND_GUIDE.md             # Backend walkthrough
├── COLLECTION_PROCESSOR_EXPLAINED.md  # Run coordination deep dive
└── RESOURCE_DETECTION.md        # Batch sizing notes
```

**Key Principles**:
- **Separation of Concerns**: API layer (HTTP) separate from business logic (utils)
- **Modular Design**: Each utility handles one responsibility (models, images, runs)
- **Database Abstraction**: All database operations in dedicated files
- **Documentation**: Complex parts have dedicated explanation docs

### Frontend (`frontend/`)

```
frontend/
├── app/                         # Next.js App Router
│   ├── layout.tsx               # Root layout + theme
│   ├── globals.css              # Global styles
│   ├── page.tsx                 # Home upload page (/)
│   ├── collection/[collectionId]/page.tsx   # Run/results dashboard
│   └── edit/[imageId]/page.tsx              # Image detail + polygon editor (requires ?runId=)
├── components/                  # UI building blocks
│   ├── home/                    # Upload/top bar/error display
│   ├── run/                     # Run status, thresholds, image list, upload controls
│   └── edit/                    # Image display, overlays, modals for polygon edits
├── hooks/                       # Data fetching and UI state (useCollectionData, useModels, useImageUpload, useRunState, etc.)
├── lib/                         # API client (`api.ts`)
├── utils/                       # Validation, storage, query helpers
└── public/                      # Static assets
```

**Key Principles**:
- **Component Isolation**: Each component handles one UI piece
- **Custom Hooks**: Business logic separate from UI rendering
- **API Abstraction**: All backend calls through `lib/api.ts`
- **Type Safety**: TypeScript for catching errors early

## Stack

### [Next.js](https://nextjs.org/)
For hosting frontend, used for serving the front end and API routing. With a React UI.  
Next.js is specially designed for React, and handles routing while Node.js needs to use Express. Also much more minimal and efficient than Node.  
Next.js is essentially Node.js + specially made for React + built-in routing + more.

### [Python FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://uvicorn.dev/)
Since our model is built using Python libraries, we need to use Python-based APIs to run it.  
FastAPI is a Python backend used to make APIs that will connect to our Next.js frontend.  
Runs in Python, used to connect our model’s inference to our frontend.  
Uvicorn is used to run these APIs on a server.  
ASGI (Asynchronous Server Gateway Interface) runs up a server to host the APIs while being able to handle async requests.  
Handles Sockets, HTTP, etc. for the API.

### [SQLite](https://sqlite.org/)
Lightweight, serverless database for storing:
- Collections and their metadata
- Image records and file hashes (for deduplication)
- Model information and optimal batch sizes
- Inference runs and their results
- Image results with mussel counts and polygon data

**Schema Features:**
- Async operations using `aiosqlite`
- Automatic database initialization from `schema.sql`
- Foreign key constraints for data integrity
- Composite primary keys for efficient run-image relationships

### [PyInstaller](https://pyinstaller.org/)
Used to bundle the application into an `.exe` file that opens the browser and runs the application.  
All Athan needs to do is download the `.exe`, and open the app.

---

## Key Features

### Smart Run Management
- **Run Reuse**: Runs are uniquely identified by `(collection_id, model_id, threshold)`
- **Incremental Processing**: Only new images are processed when restarting a run with the same configuration
- **Real-time Updates**: Image results are written to database immediately as batches complete
- **Progress Tracking**: Live updates of processed image count during inference
- **Run Cancellation**: Ability to stop ongoing runs via frontend UI

### Resource Optimization
- **CPU Thread Optimization**: Automatically configures PyTorch threading based on available CPU cores
- **Dynamic Batch Sizing**: Calculates optimal batch size based on model parameter count (not just model type)
- **Inference Optimizations**: Disables gradient tracking and unnecessary CUDA operations for faster inference
- **Non-blocking Model Loading**: Model loading runs in background thread to prevent UI freezing
- **Lazy Image Loading**: Frontend thumbnails use lazy loading for better performance

### Image Management
- **Deduplication**: Images are deduplicated by MD5 hash - same file uploaded multiple times stores only one copy
- **Async File I/O**: Uses `aiofiles` for non-blocking file operations
- **Thumbnail Display**: Image cards show thumbnails with live/dead counts and filename
- **Visual Feedback**: Color-coded indicators (orange for unprocessed, green for processed, flash animation on completion)
- **Smart Sorting**: Recently processed images automatically sort to the top during runs

### Model Support
- **Auto-Detection**: Models in `data/models/` are automatically loaded on startup
- **Multi-Model Support**: Supports Faster R-CNN and YOLO variants
- **Parameter-Based Batching**: Batch size calculated from model parameter count (e.g., YOLOv8n gets larger batches than YOLOv8x)
- **Device Detection**: Automatically uses GPU if available, optimized for CPU by default
- **Graceful Fallbacks**: Handles missing models, corrupted weights, and inference errors gracefully

---

## Pages

### Home `/`
- Drag-and-drop or picker upload for files/folders.
- Quick-process mode: creates/recalls an active collection, uploads files, and redirects to that collection’s dashboard.
- Manual create: create a fresh collection and jump to it to start a run.

### Collection Dashboard `/collection/[collectionId]`
- Shows collection totals and images with status hues (pending/processing/complete).
- Start/stop runs, choose model, and adjust threshold; supports threshold-only recalculation without rerunning the model.
- Upload more images inline, see upload progress, and manage deletions.

### Image Detail & Editing `/edit/[imageId]?runId=<runId>`
- View a single image with polygons, stats, and model/threshold context.
- Toggle overlays, open fullscreen, and reclassify polygons (live/dead) with modal confirmations.
- Link back to the source collection.

---

## APIs

### Collection Endpoints

#### `GET /api/collections`
Get all collections information.

#### `POST /api/collections`
Create a new collection.
- Request body: `{ name?: string, description?: string }`
- Returns: `{ collection_id: number }`

#### `GET /api/collections/[collectionId]`
Get all information about a certain collection.
- Returns: `{ collection: {...}, images: [...], latest_run: {...} }`
- `collection.live_mussel_count` and `collection.dead_mussel_count` represent totals from latest run (all images)
- `images[]` contains all images in the collection with their individual counts
- `latest_run` shows current run status (pending, running, completed, failed)
- Used for polling on run results page to get real-time updates

#### `POST /api/collections/[collectionId]/upload-images`
Upload image files to a collection (multipart/form-data).
- Request: `files: File[]`
- Returns: `{ collection_id: number, image_ids: number[], added_count: number, duplicate_count: number, duplicate_image_ids: number[] }`
- Images are deduplicated by hash - uploading same file twice only stores one copy
- Files are validated for type and size before processing

#### `DELETE /api/collections/[collectionId]/images/[imageId]`
Remove an image from a collection.
- Returns: `{ message: "Image removed successfully" }`
- Deletes the image file and all associated results

### Model Endpoints

#### `GET /api/models`
Get all available models.
- Returns: `[{ model_id, name, type, weights_path, description, ... }]`

#### `GET /api/models/[modelId]`
Get model information.
- Returns: `{ model_id, name, type, weights_path, description, ... }`

### Image Endpoints

#### `GET /api/images/{image_id}/results/{run_id}`
Get detailed inference results for a specific image from a specific run.
- Returns comprehensive image data including:
  - **Image metadata**: filename, dimensions, file hash, upload date
  - **Results**: live/dead counts, total count, percentages
  - **Polygon data**: Full array of bounding boxes with coordinates, labels, and confidence scores
  - **Model info**: model name, type, and threshold used
  - **Collection context**: collection ID and name for navigation
  - **Comparison data**: Other runs that processed this image (up to 10 most recent)
- Example response:
```json
{
  "image_id": 123,
  "filename": "mussel_sample.jpg",
  "width": 1920,
  "height": 1080,
  "live_mussel_count": 15,
  "dead_mussel_count": 3,
  "total_mussel_count": 18,
  "live_percentage": 83.3,
  "dead_percentage": 16.7,
  "model_name": "YOLOv8n",
  "threshold": 0.5,
  "polygons": [
    {
      "label": "live",
      "confidence": 0.95,
      "coordinates": [[100,100], [200,100], [200,200], [100,200]]
    }
  ],
  "detection_count": 18,
  "other_runs": [...]
}
```

### Run Endpoints

#### `POST /api/runs/start`
Start an inference run on a collection.
- Request body: `{ collection_id: number, model_id: number, threshold?: number }` (threshold defaults to 0.5)
- Returns: Full run object with all fields
- **Smart Run Management**: Reuses existing run if same `(collection_id, model_id, threshold)` combination exists
- Only processes images that haven't been processed for this specific run
- Runs in background - API returns immediately with run details
- Collection totals are updated when run completes

#### `GET /api/runs/[runId]`
Get specific run information.
- Returns: `{ run_id, collection_id, model_id, threshold, status, live_mussel_count, dead_mussel_count, processed_count, total_images, started_at, finished_at, error_message, ... }`
- Status can be: `pending`, `running`, `completed`, `failed`, `cancelled`

#### `POST /api/runs/[runId]/stop`
Stop/cancel a running inference run.
- Returns: Updated run object with status `cancelled`
- Only works for runs with status `pending` or `running`
- Images already processed are saved and counted

### Static File Endpoints

#### `GET /uploads/{filename}`
Serve uploaded image files.
- Returns: Image file (JPEG, PNG, etc.)
- Used for displaying image thumbnails in the frontend
- Files are served from `backend/data/uploads/` directory

---

## Documentation

- **Resource Detection System**: See `backend/RESOURCE_DETECTION.md` for detailed explanation of CPU optimization, batch size calculation, and performance tuning
- **API Documentation**: Visit http://127.0.0.1:8000/docs when backend is running for interactive API documentation

---

## Performance

### Typical Speeds (on CPU)
| Model | Parameters | Batch Size | Speed (10 images) |
|-------|-----------|-----------|-------------------|
| YOLOv8n | 3.2M | 4 | ~8 seconds |
| YOLOv8s | 11.2M | 2 | ~12 seconds |
| Faster R-CNN ResNet50 | 25M | 2 | ~35 seconds |
| YOLOv8x | 68.2M | 1 | ~35 seconds |

**Optimizations Applied:**
- CPU thread count set to `cpu_count // 3` to reduce contention
- Gradient tracking disabled during inference
- CUDA backend disabled on CPU for reduced overhead
- Batch processing for multiple images
- Non-blocking model loading in background thread

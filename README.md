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

### Dashboard `/home` or `/`
Two modes for processing images:

**Quick Process Mode:**
- Upload image(s) or folder
- Automatically creates a collection with a default name (timestamp-based) on first upload
- All subsequent uploads in the same session are added to the same collection
- Automatically adds images to the active collection
- Automatically starts inference run
- Navigates to `/run/[runId]` to show progress/results
- On run results page: can add more images → auto-starts new run → sees updated totals
- Collection totals represent cumulative count from all images (latest run)
- Collection exists but is invisible to user (can rename later if needed)
- New session or explicit collection creation starts a fresh collection

**Create Collection Mode:**
- Optional: Enter collection name and description
- Create a collection explicitly
- Upload/add images to the collection
- Navigate to `/collections/[collectionId]` where user can start a run manually
- Useful for organizing and labeling related images

### Collection History `/collections`
Lists all previous collections.  
- View all collections with basic info (name, description, image count, live mussel count)
- Search/filter collections
- Click to navigate to `/collections/[collectionId]`

### Collection View `/collections/[collectionId]`
View collection information and latest run results (read-only).  
- Display collection details (name, description, image count, live mussel count)
- Show latest run results (if exists)
- Display all images in the collection with their polygon predictions and counts
- "Start New Run" button → navigates to `/run/[runId]` (creates new run)
- Link to edit page for collection management

### Collection Edit `/collections/[collectionId]/edit`
Edit collection and manage images.  
- Add more images to the collection
- Update collection name/description
- View/manage images in the collection

### Run Results `/run/[runId]`
Display results for a collection with seamless image addition.  
- Shows **collection totals** (live_mussel_count, dead_mussel_count) - represents total across ALL images in collection
- Displays current run status (pending, running, completed, failed, cancelled) with progress
- **Stop Run** button for cancelling ongoing inference
- Lists **all images in the collection** with thumbnail previews
- Shows individual live/dead counts for each image
- **Visual Indicators**:
  - Orange hue: Image needs processing for current model/threshold combination
  - Green hue (persistent): Currently processing
  - Green flash: Just finished processing
- **Smart Sorting**: Recently processed images automatically move to the top during runs
- **"Add More Images" button** - upload more images, automatically starts new run
- When new run completes, totals update in place (no page navigation)
- **Smart Run Reuse**: Switching models or thresholds brings back orange hue for unprocessed combinations
- Run only processes images that haven't been run with current model/threshold
- Can change threshold and re-run (reuses existing run if same model/threshold)
- Model selector to switch between available models

### Image Detail `/images/[imageId]`
View detailed model stats for a specific image.  
- Display image with polygon overlays
- Show live and dead mussel counts
- Change threshold for this image (creates new run)
- View image metadata (filename, dimensions, etc.)
- Maybe relabel images (future feature)

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

#### `GET /api/images/[imageId]`
Get image information from inference.
- Returns: `{ image_id, filename, stored_path, live_mussel_count, dead_mussel_count, ... }`

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

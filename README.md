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
pip install fastapi uvicorn aiosqlite
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
source venv/bin/activate
uvicorn main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

- Backend: http://127.0.0.1:8000
- Frontend: http://localhost:3000

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
For storing data.

### [PyInstaller](https://pyinstaller.org/)
Used to bundle the application into an `.exe` file that opens the browser and runs the application.  
All Athan needs to do is download the `.exe`, and open the app.

---

## Pages

### Dashboard `/home` or `/`
Two modes for processing images:

**Quick Process Mode:**
- Upload image(s) or folder
- Automatically creates batch with default name (timestamp-based) on first upload
- All subsequent uploads in the same session are added to the same batch
- Automatically adds images to batch
- Automatically starts inference run
- Navigates to `/run/[runId]` to show progress/results
- Batch exists but is invisible to user (can rename later if needed)
- New session or explicit batch creation starts a fresh batch

**Create Batch Mode:**
- Optional: Enter batch name and description
- Create batch explicitly
- Upload/add images to batch
- Navigate to `/batches/[batchId]` where user can start a run manually
- Useful for organizing and labeling related images

### Batch History `/batches`
Lists all previous batches.  
- View all batches with basic info (name, description, image count, live mussel count)
- Search/filter batches
- Click to navigate to `/batches/[batchId]`

### Batch View `/batches/[batchId]`
View batch information and latest run results (read-only).  
- Display batch details (name, description, image count, live mussel count)
- Show latest run results (if exists)
- Display all images in batch with their polygon predictions and counts
- "Start New Run" button → navigates to `/run/[runId]` (creates new run)
- Link to edit page for batch management

### Batch Edit `/batches/[batchId]/edit`
Edit batch and manage images.  
- Add more images to the batch
- Update batch name/description
- View/manage images in batch

### Run Results `/run/[runId]`
Run inference and display results for a specific run.  
- Shows run status (pending, running, completed, failed)
- Displays progress during inference
- Lists all images processed in this run
- Shows polygon predictions on each image
- Displays live and dead mussel counts per image
- Shows total counts for the run
- Can change threshold and re-run (creates new run)

### Image Detail `/images/[imageId]`
View detailed model stats for a specific image.  
- Display image with polygon overlays
- Show live and dead mussel counts
- Change threshold for this image (creates new run)
- View image metadata (filename, dimensions, etc.)
- Maybe relabel images (future feature)

---

## APIs

### Batch Endpoints

#### `GET /api/batches`
Get all batches information.

#### `POST /api/batches`
Create a new batch.
- Request body: `{ name?: string, description?: string }`
- Returns: `{ batch_id: number }`

#### `GET /api/batches/[batchId]`
Get all information about a certain batch.
- Returns: `{ batch: {...}, images: [...], latest_run: {...} }`

#### `POST /api/batches/[batchId]/upload-images`
Upload image files to a batch (multipart/form-data).
- Request: `files: File[]`
- Returns: `{ batch_id: number, image_ids: number[], count: number }`

#### `POST /api/batches/[batchId]/run`
Start an inference run on a batch.
- Request body: `{ model_id: number, threshold: number }`
- Returns: `{ run_id: number, ... }` (to be implemented)

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

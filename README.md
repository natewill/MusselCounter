# Muscle Counter Capstone Project

## Stack

### [Next.js](https://nextjs.org/)
Used for hosting the frontend and API routing.  
Provides a **React-based UI** for users to interact with the application.

### [Python FastAPI](https://fastapi.tiangolo.com/#sponsors) + [Uvicorn](https://uvicorn.dev/)
Since our model is built using Python libraries, we need to use a Python-based API to run it.  
- **FastAPI** is the Python backend framework used to create APIs that connect to our Next.js frontend.  
- **Uvicorn** is used to run these APIs on a local server.

### [SQLite](https://sqlite.org/)
Used for storing batch, image, and inference data.

### [PyInstaller](https://pyinstaller.org/)
Used to bundle the application into a **single `.exe` file** that automatically opens the browser and runs the application locally.

---

## Pages

### Dashboard
- Upload an image, multiple images, or a folder of images.

### Results Page `/batches/[batchId]`
- Runs inference on image(s) and lists all images with the model’s polygon predictions.  
- Displays live muscle count.  
- Allows changing the **score threshold** for classifying dead or alive muscles.  
- Ability to **add more images** to the batch and **run more inference**.

### Batch History / Library `/batches`
- Lists all previous batches.  
- Allows opening a batch and navigating to its `batchId`.  
- Search functionality to find batches.

### Images `/images/[imageId]`
- View model stats of a certain image.  
- Change threshold for the image.  
- (Future) Possibly relabel or correct model predictions.

---

## APIs

### `GET /api/batches`
Get all batches information.

### `GET /api/batches/[batchId]`
Get all information about a specific batch.

### `POST /api/batches/[batchId]/add-images`
Add more files to an existing batch.

### `POST /api/batches/[batchId]/run`
Run inference on a batch.

### `GET /api/images/[imageId]`
Get image information from inference results.

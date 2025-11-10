# Muscle Counter Application

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

### Dashboard `/home`
Upload an image, multiple images, or a folder of images.

### Results Page `/batches/[batchId]`
Runs inference on image(s), and lists all images with the model’s polygon predictions on each image, with a live muscle count.  
Able to change the score threshold for classifying dead or alive.  
Add more images to the batch and run more inference.

### Batch History or Library `/batches`
Lists all previous batches.  
Able to open batches and go to their `batchId`.  
Able to search for batches.

### Images `/images/[imageId]`
See model stats of a certain image.  
Change threshold for image.  
Maybe be able to relabel images but idk maybe later.

---

## APIs

### `GET /api/batches`
Get all batches information.

### `GET /api/batches/[batchId]`
Get all information about a certain batch.

### `POST /api/batches/[batchId]/add-images`
Add more files to existing batch.

### `POST /api/batches/[batchId]/run`
Run inference on batch.

### `GET /api/images/[imageId]`
Get image information from inference.

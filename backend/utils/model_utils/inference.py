"""
Model inference functions for running object detection on images.

This module contains the actual code that runs ML models on images to detect mussels.
It handles both Faster R-CNN and YOLO models, processing their outputs into a standard format.

Key Concepts:
- Bounding Box: Rectangle around a detected mussel (x1, y1, x2, y2)
- Confidence: How sure the model is (0.0 to 1.0)
- Threshold: Minimum confidence to keep a detection
- Polygon: 4 corner points of bounding box (for drawing on frontend)

Process Overview:
1. Load image(s) from disk
2. Convert to format model expects (tensors for PyTorch)
3. Run model to get predictions
4. Filter predictions by confidence threshold
5. Count live vs dead detections
6. Convert bounding boxes to polygons
7. Return standardized results
"""

import torch
import torchvision.transforms as transforms
from PIL import Image


# Label mappings - different models use different class numbers
# R-CNN: 0=background, 1=live, 2=dead
# YOLO: 0=live, 1=dead (no background class)
RCNN_LABELS = {1: "live", 2: "dead"}
YOLO_LABELS = {0: "live", 1: "dead"}


def _rectangle(box):
    """
    Convert bounding box to polygon (4 corner points).
    
    Bounding boxes are stored as [x1, y1, x2, y2]:
    - (x1, y1) = top-left corner
    - (x2, y2) = bottom-right corner
    
    Polygons are 4 points going clockwise from top-left:
    - Top-left, Top-right, Bottom-right, Bottom-left
    
    This format is easier for the frontend to draw on images.
    
    Args:
        box: [x1, y1, x2, y2] coordinates
        
    Returns:
        List of 4 corner points: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
        
    Example:
        _rectangle([100, 200, 150, 250])
        # Returns: [[100,200], [150,200], [150,250], [100,250]]
    """
    x1, y1, x2, y2 = box
    return [
        [float(x1), float(y1)],  # Top-left
        [float(x2), float(y1)],  # Top-right
        [float(x2), float(y2)],  # Bottom-right
        [float(x1), float(y2)],  # Bottom-left
    ]


def _result(live, dead, polygons, size):
    """
    Create standardized result dictionary for an image.
    
    This format is used consistently across all model types,
    making it easy for the rest of the codebase to work with results.
    
    Args:
        live: Number of live mussels detected
        dead: Number of dead mussels detected
        polygons: List of detection polygons with metadata
        size: (width, height) of the image
        
    Returns:
        Dictionary with counts, polygons, and image dimensions
        
    Example:
        _result(5, 2, [...polygons...], (1920, 1080))
        # Returns: {
        #     "live_count": 5,
        #     "dead_count": 2,
        #     "polygons": [...],
        #     "image_width": 1920,
        #     "image_height": 1080
        # }
    """
    width, height = size
    return {
        "live_count": live,
        "dead_count": dead,
        "polygons": polygons,
        "polygon_path": None,  # Will be set later when saving to file
        "image_width": width,
        "image_height": height,
    }


def _run_rcnn(model_device_tuple, image_paths):
    """
    Run Faster R-CNN inference on a batch of images.
    
    How It Works:
    1. Load all images and convert to tensors (PyTorch format)
    2. Run model on all images at once (batch processing)
    3. For each image's predictions:
       - Get ALL detections (no threshold filtering)
       - Count live vs dead detections
       - Convert bounding boxes to polygons
       - Save all detection metadata
    
    R-CNN Output Format:
    - boxes: [[x1, y1, x2, y2], ...]  # Bounding box coordinates
    - scores: [0.95, 0.87, ...]        # Confidence scores
    - labels: [1, 2, 1, ...]            # Class IDs (1=live, 2=dead)
    
    Args:
        model_device_tuple: (model, device, batch_size) from loader
        image_paths: List of paths to image files
        
    Returns:
        List of result dicts, one per image
        
    Example:
        results = _run_rcnn(model_tuple, ["img1.jpg", "img2.jpg"])
        # Returns: [
        #   {"live_count": 5, "dead_count": 2, "polygons": [...], ...},
        #   {"live_count": 3, "dead_count": 1, "polygons": [...], ...}
        # ]
    """
    # Unpack model and device (ignore batch_size, that's just metadata)
    model, device = model_device_tuple[:2]
    
    # Prepare to convert images to PyTorch tensors
    transform = transforms.ToTensor()
    tensors = []  # Will hold image tensors
    sizes = []    # Will hold original (width, height) for each image
    
    # Load and convert all images
    for path in image_paths:
        image = Image.open(path).convert("RGB")  # Ensure RGB format
        sizes.append(image.size)  # Save original dimensions
        tensors.append(transform(image).to(device))  # Convert and move to device
    
    # Run inference on all images at once (batch processing)
    # no_grad() means don't track gradients (we're not training)
    with torch.no_grad():
        predictions = model(tensors)
    
    # Process predictions for each image
    results = []
    for size, pred in zip(sizes, predictions):
        live = dead = 0  # Counters
        polygons = []    # List of detections with metadata
        
        # Convert predictions from GPU tensors to CPU numpy arrays
        boxes = pred["boxes"].cpu().numpy()    # Bounding boxes
        scores = pred["scores"].cpu().numpy()  # Confidence scores
        labels = pred["labels"].cpu().numpy()  # Class IDs
        
        # Process each detection
        # Note: We always get ALL detections (threshold filtering happens later for display)
        for box, score, label in zip(boxes, scores, labels):
            # Convert class ID to label string (1→"live", 2→"dead")
            cls = RCNN_LABELS.get(int(label))
            
            # Count the detection
            if cls == "live":
                live += 1
            elif cls == "dead":
                dead += 1
            else:
                continue  # Skip if not live or dead (e.g., background)
            
            # Save detection with all metadata
            polygons.append(
                {
                    "coords": _rectangle(box.tolist()),  # 4 corner points
                    "confidence": float(score),           # How sure the model is
                    "class": cls,                         # "live" or "dead"
                    "bbox": [float(v) for v in box],     # Original box coordinates
                }
            )
        
        # Create result dict for this image
        results.append(_result(live, dead, polygons, size))
    
    # Clean up GPU memory if using CUDA
    if device.type == "cuda":
        torch.cuda.empty_cache()
    
    return results


def run_rcnn_inference_batch(model_device_tuple, image_paths: list[str]):
    """
    Run R-CNN on multiple images (batch processing).
    
    This is the main function called by collection_processor.py when processing
    multiple images. It's more efficient than processing one-by-one.
    
    Always returns ALL detections (no threshold filtering).
    Threshold filtering happens later when querying the database.
    
    Public API for batch processing.
    """
    return _run_rcnn(model_device_tuple, image_paths)


def run_rcnn_inference(model_device_tuple, image_path: str):
    """
    Run R-CNN on a single image.
    
    This is a convenience wrapper that calls the batch function with one image.
    Used by image_processor.py for single-image processing (fallback path).
    
    Always returns ALL detections (no threshold filtering).
    Threshold filtering happens later when querying the database.
    
    Public API for single image processing.
    """
    return _run_rcnn(model_device_tuple, [image_path])[0]


def _run_yolo(model_device_tuple, image_paths):
    """
    Run YOLO inference on images.
    
    YOLO is Different from R-CNN:
    - Faster (processes entire image in one pass)
    - Returns results in a different format
    - Generally more efficient for real-time detection
    
    YOLO Output Format:
    - Each detection has a `boxes` object with:
      - xyxy: [x1, y1, x2, y2] coordinates
      - conf: confidence score
      - cls: class ID (0=live, 1=dead)
    
    Args:
        model_device_tuple: (model, device, batch_size) from loader
        image_paths: Single path or list of paths
        
    Returns:
        List of result dicts, one per image
        
    Example:
        results = _run_yolo(model_tuple, ["img1.jpg"])
        # Returns: [{"live_count": 3, "dead_count": 1, ...}]
    """
    # Unpack model (YOLO doesn't need explicit device handling)
    model, _ = model_device_tuple[:2]
    
    # Ensure we have a list (YOLO can handle both single and batch)
    paths = image_paths if isinstance(image_paths, list) else [image_paths]
    
    # Run YOLO inference
    # conf=0.0: Always get ALL detections (threshold filtering happens later for display)
    # verbose=False: Don't print progress to console
    detections = model(paths, conf=0.0, verbose=False)
    
    # Process results for each image
    outputs = []
    for path, det in zip(paths, detections):
        # Get image dimensions (needed for result dict)
        width, height = Image.open(path).size
        
        live = dead = 0  # Counters
        polygons = []    # List of detections
        
        # Process each detection box
        for box in det.boxes:
            # Get confidence score
            confidence = float(box.conf[0].cpu().numpy())
            
            # Note: We always get ALL detections (threshold filtering happens later for display)
            # Get class label (0=live, 1=dead)
            cls = YOLO_LABELS.get(int(box.cls[0].cpu().numpy()))
            
            # Count the detection
            if cls == "live":
                live += 1
            elif cls == "dead":
                dead += 1
            else:
                continue  # Skip unknown classes
            
            # Get bounding box coordinates
            # xyxy format: [x1, y1, x2, y2]
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            
            # Save detection with all metadata
            polygons.append(
                {
                    "coords": _rectangle([x1, y1, x2, y2]),  # 4 corner points
                    "confidence": confidence,                 # Model confidence
                    "class": cls,                            # "live" or "dead"
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],  # Box coords
                }
            )
        
        # Create result dict for this image
        outputs.append(_result(live, dead, polygons, (width, height)))
    
    return outputs


def run_yolo_inference(model_device_tuple, image_path: str):
    """
    Run YOLO on a single image.
    
    Convenience wrapper for single-image processing.
    Always returns ALL detections (no threshold filtering).
    Threshold filtering happens later when querying the database.
    
    Public API - called by image_processor.py
    """
    return _run_yolo(model_device_tuple, [image_path])[0]


def run_yolo_inference_batch(model_device_tuple, image_paths: list[str]):
    """
    Run YOLO on multiple images (batch processing).
    
    Main function for batch processing with YOLO.
    Always returns ALL detections (no threshold filtering).
    Threshold filtering happens later when querying the database.
    
    Public API - called by collection_processor.py
    """
    return _run_yolo(model_device_tuple, image_paths)


def run_ssd_inference(model_device_tuple, image_path: str):
    """SSD (Single Shot Detector) inference - not yet implemented."""
    raise NotImplementedError("SSD inference not implemented.")


def run_cnn_inference(model_device_tuple, image_path: str):
    """CNN detection inference - not yet implemented."""
    raise NotImplementedError("CNN detection inference not implemented.")


def run_inference_on_image(model_device_tuple, image_path: str, model_type: str):
    """
    Main entry point for running inference on a single image.
    
    This function acts as a router - it looks at the model_type
    and calls the appropriate inference function (R-CNN, YOLO, etc.).
    
    Used By:
    - image_processor.py for single-image processing (legacy/fallback)
    
    Why This Exists:
    - Provides a unified interface for all model types
    - Makes it easy to add new model types (just add a case here)
    - Handles model type string variations (case-insensitive, partial matches)
    
    Args:
        model_device_tuple: (model, device, batch_size) from loader
        image_path: Path to the image file
        model_type: Type of model as string (e.g., "YOLO", "Faster R-CNN")
        
    Returns:
        Result dict with counts, polygons, and image dimensions
        Always returns ALL detections (no threshold filtering).
        Threshold filtering happens later when querying the database.
        
    Raises:
        ValueError: If model_type is not supported
        
    Example:
        result = run_inference_on_image(model_tuple, "mussel.jpg", "YOLO")
        # Returns: {"live_count": 5, "dead_count": 2, "polygons": [...], ...}
    """
    # Convert to lowercase for case-insensitive matching
    model_type_lower = model_type.lower()
    
    # Route to appropriate inference function
    # Uses partial string matching for flexibility
    if "rcnn" in model_type_lower or "faster" in model_type_lower:
        return run_rcnn_inference(model_device_tuple, image_path)
    if "yolo" in model_type_lower:
        return run_yolo_inference(model_device_tuple, image_path)
    if "ssd" in model_type_lower:
        return run_ssd_inference(model_device_tuple, image_path)
    if "cnn" in model_type_lower and "rcnn" not in model_type_lower:
        return run_cnn_inference(model_device_tuple, image_path)
    
    # Model type not recognized
    raise ValueError(
        f"Unsupported model type: {model_type}. "
        "Supported types: RCNN, YOLO, SSD, CNN (object detection models only)."
    )

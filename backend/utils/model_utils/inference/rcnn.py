"""
FASTRCNN inference adapter implementation.
"""

from PIL import Image
import torch
import torchvision.transforms as transforms
from .common import RCNN_LABELS, convert_to_dictionary


def _run_rcnn(model_device_tuple, image_paths):
    """
    Run Faster R-CNN inference on a batch of images.

    How It Works:
    1. Load all images and convert to tensors (PyTorch format)
    2. Run model on all images at once (batch processing)
    3. For each image's predictions:
       - Get ALL detections (no threshold filtering)
       - Count live vs dead detections
       - Keep bbox coordinates directly
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
    model, device = model_device_tuple[:2]
    transform = transforms.ToTensor()
    tensors = []

    for path in image_paths:
        image = Image.open(path).convert("RGB")
        tensors.append(transform(image).to(device))

    with torch.no_grad():
        predictions = model(tensors)

    outputs = []
    for pred in predictions:
        live = dead = 0
        polygons = []

        boxes = pred["boxes"].cpu().numpy()
        scores = pred["scores"].cpu().numpy()
        labels = pred["labels"].cpu().numpy()

        for box, score, label in zip(boxes, scores, labels):
            cls = RCNN_LABELS.get(int(label))
            if cls == "live":
                live += 1
            elif cls == "dead":
                dead += 1
            else:
                continue

            polygons.append(
                {
                    "confidence": float(score),
                    "class": cls,
                    "bbox": [float(v) for v in box],
                }
            )

        outputs.append(convert_to_dictionary(live, dead, polygons))

    if device.type == "cuda":
        torch.cuda.empty_cache()

    return outputs


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

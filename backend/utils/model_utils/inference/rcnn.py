"""
FASTRCNN inference adapter implementation.
"""

from PIL import Image
import torch
import torchvision.transforms as transforms
from .common import RCNN_LABELS, convert_to_dictionary


def _run_rcnn(model_device_tuple, image_path: str):
    """
    Run Faster R-CNN inference on a single image.

    How It Works:
    1. Load one image and convert it to a PyTorch tensor
    2. Run model inference
    3. Convert detections into the shared result shape

    R-CNN Output Format:
    - boxes: [[x1, y1, x2, y2], ...]  # Bounding box coordinates
    - scores: [0.95, 0.87, ...]        # Confidence scores
    - labels: [1, 2, 1, ...]            # Class IDs (1=live, 2=dead)

    Args:
        model_device_tuple: (model, device) from loader
        image_path: Path to one image file

    Returns:
        Standardized inference result dict for one image.
    """
    model, device = model_device_tuple[:2]
    transform = transforms.ToTensor()
    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).to(device)

    with torch.no_grad():
        pred = model([tensor])[0]

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

    if device.type == "cuda":
        torch.cuda.empty_cache()

    return convert_to_dictionary(live, dead, polygons)


def run_rcnn_inference(model_device_tuple, image_path: str):
    """
    Run R-CNN on a single image.

    Public API for single-image processing.
    """
    return _run_rcnn(model_device_tuple, image_path)

"""
YOLO inference adapter implementation.
"""

from .common import YOLO_LABELS, convert_to_dictionary


def _run_yolo(model_device_tuple, image_paths: list[str]):
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
        image_paths: List of image file paths

    Returns:
        List of result dicts, one per image

    Example:
        results = _run_yolo(model_tuple, ["img1.jpg"])
        # Returns: [{"live_count": 3, "dead_count": 1, ...}]
    """
    model, _ = model_device_tuple[:2]
    detections = model(image_paths, conf=0.01, verbose=False)

    outputs = []
    for det in detections:
        live = dead = 0
        polygons = []

        for box in det.boxes:
            confidence = float(box.conf[0].cpu().numpy())
            cls = YOLO_LABELS.get(int(box.cls[0].cpu().numpy()))

            if cls == "live":
                live += 1
            elif cls == "dead":
                dead += 1
            else:
                continue

            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            polygons.append(
                {
                    "confidence": confidence,
                    "class": cls,
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                }
            )

        outputs.append(convert_to_dictionary(live, dead, polygons))

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

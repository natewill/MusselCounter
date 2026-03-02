"""
YOLO inference adapter implementation.
"""

from .common import YOLO_LABELS, convert_to_dictionary


def run_yolo_inference(model_device_tuple, image_path: str):
    """
    Run YOLO inference on a single image.

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
        model_device_tuple: (model, device) from loader
        image_path: Path to one image file

    Returns:
        Standardized inference result dict for one image.
    """
    model, _ = model_device_tuple[:2]
    detections = model([image_path], conf=0.01, verbose=False)
    det = detections[0]

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

    return convert_to_dictionary(live, dead, polygons)

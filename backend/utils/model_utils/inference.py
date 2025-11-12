import torch
import torchvision.transforms as transforms
from PIL import Image


RCNN_LABELS = {1: "live", 2: "dead"}
YOLO_LABELS = {0: "live", 1: "dead"}


def _rectangle(box):
    x1, y1, x2, y2 = box
    return [
        [float(x1), float(y1)],
        [float(x2), float(y1)],
        [float(x2), float(y2)],
        [float(x1), float(y2)],
    ]


def _result(live, dead, polygons, size):
    width, height = size
    return {
        "live_count": live,
        "dead_count": dead,
        "polygons": polygons,
        "polygon_path": None,
        "image_width": width,
        "image_height": height,
    }


def _run_rcnn(model_device_tuple, image_paths, threshold):
    model, device = model_device_tuple[:2]  # Unpack only model and device, ignore batch_size
    transform = transforms.ToTensor()
    tensors = []
    sizes = []
    for path in image_paths:
        image = Image.open(path).convert("RGB")
        sizes.append(image.size)
        tensors.append(transform(image).to(device))
    with torch.no_grad():
        predictions = model(tensors)
    results = []
    for size, pred in zip(sizes, predictions):
        live = dead = 0
        polygons = []
        boxes = pred["boxes"].cpu().numpy()
        scores = pred["scores"].cpu().numpy()
        labels = pred["labels"].cpu().numpy()
        for box, score, label in zip(boxes, scores, labels):
            if score < threshold:
                continue
            cls = RCNN_LABELS.get(int(label))
            if cls == "live":
                live += 1
            elif cls == "dead":
                dead += 1
            else:
                continue
            polygons.append(
                {
                    "coords": _rectangle(box.tolist()),
                    "confidence": float(score),
                    "class": cls,
                    "bbox": [float(v) for v in box],
                }
            )
        results.append(_result(live, dead, polygons, size))
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return results


def run_rcnn_inference_batch(model_device_tuple, image_paths: list[str], threshold: float):
    return _run_rcnn(model_device_tuple, image_paths, threshold)


def run_rcnn_inference(model_device_tuple, image_path: str, threshold: float):
    return _run_rcnn(model_device_tuple, [image_path], threshold)[0]


def _run_yolo(model_device_tuple, image_paths, threshold):
    model, _ = model_device_tuple[:2]  # Unpack only model and device, ignore batch_size
    paths = image_paths if isinstance(image_paths, list) else [image_paths]
    detections = model(paths, conf=threshold, verbose=False)
    outputs = []
    for path, det in zip(paths, detections):
        width, height = Image.open(path).size
        live = dead = 0
        polygons = []
        for box in det.boxes:
            confidence = float(box.conf[0].cpu().numpy())
            if confidence < threshold:
                continue
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
                    "coords": _rectangle([x1, y1, x2, y2]),
                    "confidence": confidence,
                    "class": cls,
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                }
            )
        outputs.append(_result(live, dead, polygons, (width, height)))
    return outputs


def run_yolo_inference(model_device_tuple, image_path: str, threshold: float):
    return _run_yolo(model_device_tuple, image_path, threshold)[0]


def run_yolo_inference_batch(model_device_tuple, image_paths: list[str], threshold: float):
    return _run_yolo(model_device_tuple, image_paths, threshold)


def run_ssd_inference(model_device_tuple, image_path: str, threshold: float):
    raise NotImplementedError("SSD inference not implemented.")


def run_cnn_inference(model_device_tuple, image_path: str, threshold: float):
    raise NotImplementedError("CNN detection inference not implemented.")


def run_inference_on_image(model_device_tuple, image_path: str, threshold: float, model_type: str):
    model_type_lower = model_type.lower()
    if "rcnn" in model_type_lower or "faster" in model_type_lower:
        return run_rcnn_inference(model_device_tuple, image_path, threshold)
    if "yolo" in model_type_lower:
        return run_yolo_inference(model_device_tuple, image_path, threshold)
    if "ssd" in model_type_lower:
        return run_ssd_inference(model_device_tuple, image_path, threshold)
    if "cnn" in model_type_lower and "rcnn" not in model_type_lower:
        return run_cnn_inference(model_device_tuple, image_path, threshold)
    raise ValueError(
        f"Unsupported model type: {model_type}. "
        "Supported types: RCNN, YOLO, SSD, CNN (object detection models only)."
    )


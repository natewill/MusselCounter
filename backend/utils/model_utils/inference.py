import torch
import torchvision.transforms as transforms
from PIL import Image
import numpy as np


def run_rcnn_inference(model_device_tuple, image_path: str, threshold: float):
    """
    Run Faster R-CNN inference on a single image.
    
    Args:
        model_device_tuple: Tuple of (model, device) from load_model
        image_path: Path to image file
        threshold: Threshold score for classification
        
    Returns:
        Dictionary with live_count, dead_count, polygons, etc.
    """
    model, device = model_device_tuple
    
    # Load and preprocess image
    try:
        image = Image.open(image_path).convert('RGB')
        image_array = np.array(image)
        original_height, original_width = image_array.shape[:2]
    except Exception as e:
        raise RuntimeError(f"Failed to load image {image_path}: {str(e)}")
    
    # Convert PIL image to tensor
    transform = transforms.Compose([transforms.ToTensor()])
    image_tensor = transform(image).to(device)
    
    # Run inference
    with torch.no_grad():
        predictions = model([image_tensor])
    
    # Process predictions
    pred = predictions[0]
    
    live_count = 0
    dead_count = 0
    polygons = []
    
    boxes = pred['boxes'].cpu().numpy()
    scores = pred['scores'].cpu().numpy()
    labels = pred['labels'].cpu().numpy()
    
    for box, score, label in zip(boxes, scores, labels):
        if score < threshold:
            continue
        
        # Label mapping: 0=background, 1=live, 2=dead
        if label == 1:
            class_name = 'live'
            live_count += 1
        elif label == 2:
            class_name = 'dead'
            dead_count += 1
        else:
            continue
        
        x1, y1, x2, y2 = box.tolist()
        polygon_coords = [
            [x1, y1], [x2, y1], [x2, y2], [x1, y2]
        ]
        
        polygons.append({
            'coords': polygon_coords,
            'confidence': float(score),
            'class': class_name,
            'bbox': [float(x1), float(y1), float(x2), float(y2)]
        })
    
    return {
        'live_count': live_count,
        'dead_count': dead_count,
        'polygons': polygons,
        'polygon_path': None,
        'image_width': original_width,
        'image_height': original_height
    }


def run_yolo_inference(model_device_tuple, image_path: str, threshold: float):
    """
    Run YOLO inference on a single image.
    
    Args:
        model_device_tuple: Tuple of (model, device) from load_model
        image_path: Path to image file
        threshold: Threshold score for classification
        
    Returns:
        Dictionary with live_count, dead_count, polygons, etc.
        
    TODO: Implement YOLO inference.
    YOLO outputs bounding boxes that need to be converted to polygons.
    """
    raise NotImplementedError(
        "YOLO inference not implemented. "
        "Please implement run_yolo_inference() for YOLO model inference."
    )


def run_ssd_inference(model_device_tuple, image_path: str, threshold: float):
    """
    Run SSD inference on a single image.
    
    Args:
        model_device_tuple: Tuple of (model, device) from load_model
        image_path: Path to image file
        threshold: Threshold score for classification
        
    Returns:
        Dictionary with live_count, dead_count, polygons, etc.
        
    TODO: Implement SSD inference.
    SSD outputs bounding boxes that need to be converted to polygons.
    """
    raise NotImplementedError(
        "SSD inference not implemented. "
        "Please implement run_ssd_inference() for SSD model inference."
    )


def run_cnn_inference(model_device_tuple, image_path: str, threshold: float):
    """
    Run CNN detection inference on a single image.
    
    Args:
        model_device_tuple: Tuple of (model, device) from load_model
        image_path: Path to image file
        threshold: Threshold score for classification
        
    Returns:
        Dictionary with live_count, dead_count, polygons, etc.
        
    Note: This assumes a CNN-based object detection model, not a classification CNN.
    TODO: Implement CNN detection inference.
    CNN detection outputs bounding boxes that need to be converted to polygons.
    """
    raise NotImplementedError(
        "CNN detection inference not implemented. "
        "Please implement run_cnn_inference() for CNN detection model inference."
    )


def run_inference_on_image(model_device_tuple, image_path: str, threshold: float, model_type: str):
    """
    Run inference on a single image based on model type.
    
    Args:
        model_device_tuple: Tuple of (model, device) from load_model
        image_path: Path to image file
        threshold: Threshold score for classification
        model_type: Type of model ('RCNN', 'YOLO', 'SSD', 'CNN', etc.)
        
    Returns:
        Dictionary with:
        - live_count: int - Number of live mussels detected
        - dead_count: int - Number of dead mussels detected
        - polygons: list - List of polygon dictionaries with coords, confidence, class
        - polygon_path: str - Path where polygon data will be saved
        - image_width: int
        - image_height: int
        
    All models must be object detection models that output bounding boxes/polygons.
    """
    model_type_lower = model_type.lower()
    
    # Route to appropriate inference function
    if 'rcnn' in model_type_lower or 'faster' in model_type_lower:
        return run_rcnn_inference(model_device_tuple, image_path, threshold)
    elif 'yolo' in model_type_lower:
        return run_yolo_inference(model_device_tuple, image_path, threshold)
    elif 'ssd' in model_type_lower:
        return run_ssd_inference(model_device_tuple, image_path, threshold)
    elif 'cnn' in model_type_lower and 'rcnn' not in model_type_lower:
        return run_cnn_inference(model_device_tuple, image_path, threshold)
    else:
        raise ValueError(
            f"Unsupported model type: {model_type}. "
            f"Supported types: RCNN, YOLO, SSD, CNN (all must be object detection models)"
        )


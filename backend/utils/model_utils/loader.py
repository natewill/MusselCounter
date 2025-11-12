import logging
import torch
from torchvision.models.detection import fasterrcnn_resnet50_fpn

logger = logging.getLogger(__name__)


def _load_checkpoint(weights_path: str, device: torch.device):
    checkpoint = torch.load(weights_path, map_location=device)
    if isinstance(checkpoint, dict):
        for key in ("model_state_dict", "state_dict"):
            if key in checkpoint:
                return checkpoint[key]
    return checkpoint


def load_rcnn_model(weights_path: str, model_type: str):
    """Load R-CNN model and calculate optimal batch size based on model parameters."""
    from ..resource_detector import calculate_batch_size_from_model
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = fasterrcnn_resnet50_fpn(pretrained=False, num_classes=3)
    try:
        model.load_state_dict(_load_checkpoint(weights_path, device))
    except Exception as exc:  # pragma: no cover - log and re-raise
        raise RuntimeError(f"Failed to load R-CNN model weights from {weights_path}: {exc}")
    model.to(device)
    model.eval()
    
    # Inference optimizations: disable gradient tracking and unnecessary operations
    torch.set_grad_enabled(False)  # Don't track gradients (inference only)
    if device.type == 'cpu':
        # CPU-specific optimizations to reduce overhead
        torch.backends.cudnn.enabled = False
    
    logger.debug(f"[Model Loader] R-CNN model loaded on {device} with inference optimizations")
    
    # Calculate batch size based on actual model size (parameter count)
    batch_size = calculate_batch_size_from_model(model, device)
    return model, device, batch_size


def load_yolo_model(weights_path: str, model_type: str):
    """Load YOLO model and calculate optimal batch size based on model parameters."""
    from ..resource_detector import calculate_batch_size_from_model
    
    try:
        from ultralytics import YOLO
    except ImportError as exc:  # pragma: no cover - configuration error
        raise ImportError("ultralytics not installed. Install it with: pip install ultralytics") from exc
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = YOLO(weights_path)
    if hasattr(model, "model") and hasattr(model.model, "fuse"):
        original_fuse = model.model.fuse
        
        def safe_fuse(*args, **kwargs):
            try:
                return original_fuse(*args, **kwargs)
            except AttributeError as exc:  # pragma: no cover - compatibility path
                if "'Conv' object has no attribute 'bn'" in str(exc):
                    logger.warning("Model fusing skipped (PyTorch compatibility issue)")
                    return model.model
                raise
        
        model.model.fuse = safe_fuse
    if hasattr(model.model, "to"):
        model.model.to(device)
    model.model.eval()
    
    # Inference optimizations: disable gradient tracking and unnecessary operations
    torch.set_grad_enabled(False)  # Don't track gradients (inference only)
    if device.type == 'cpu':
        # CPU-specific optimizations to reduce overhead
        torch.backends.cudnn.enabled = False
    
    logger.debug(f"[Model Loader] YOLO model loaded on {device} with inference optimizations")
    
    # Calculate batch size based on actual model size (parameter count)
    # Note: YOLO models wrap the actual model in model.model
    actual_model = model.model if hasattr(model, 'model') else model
    batch_size = calculate_batch_size_from_model(actual_model, device)
    return model, device, batch_size


def load_ssd_model(weights_path: str):  # pragma: no cover - placeholder
    raise NotImplementedError("SSD model loading not implemented.")


def load_cnn_model(weights_path: str):  # pragma: no cover - placeholder
    raise NotImplementedError("CNN detection model loading not implemented.")


def load_model(weights_path: str, model_type: str):
    """Load model and get default batch size based on available hardware.
    
    Uses sensible defaults optimized for CPU but supports GPU if available.
    No runtime detection needed - instant loading.
    
    Args:
        weights_path: Path to model weights
        model_type: Type of model (RCNN, YOLO, etc.)
        
    Returns:
        Tuple of (model, device, batch_size)
    """
    model_type_lower = model_type.lower()
    if "rcnn" in model_type_lower or "faster" in model_type_lower:
        return load_rcnn_model(weights_path, model_type)
    if "yolo" in model_type_lower:
        return load_yolo_model(weights_path, model_type)
    if "ssd" in model_type_lower:
        return load_ssd_model(weights_path)
    if "cnn" in model_type_lower and "rcnn" not in model_type_lower:
        return load_cnn_model(weights_path)
    raise ValueError(
        f"Unsupported model type: {model_type}. Supported types: RCNN, YOLO, SSD, CNN."
    )

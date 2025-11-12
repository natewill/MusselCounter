import logging
from pathlib import Path
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


def _detect_optimal_batch_size(model, model_type: str, device) -> int:
    """Detect optimal batch size for a model"""
    from ..resource_detector import auto_bs
    
    device_str = str(device)
    
    try:
        if "yolo" in model_type.lower():
            optimal_bs = auto_bs(model, lambda bs: torch.randn(bs, 3, 640, 640), start=64, device=device_str)
        elif "rcnn" in model_type.lower() or "faster" in model_type.lower():
            optimal_bs = auto_bs(model, lambda bs: [torch.randn(3, 800, 600) for _ in range(bs)], start=16, device=device_str)
        else:
            optimal_bs = 8
        return optimal_bs
    except Exception as e:
        logger.warning(f"Batch size detection failed, using default 8: {e}")
        return 8


def load_rcnn_model(weights_path: str, detect_batch_size: bool = False, optimal_batch_size: int = None):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = fasterrcnn_resnet50_fpn(pretrained=False, num_classes=3)
    try:
        model.load_state_dict(_load_checkpoint(weights_path, device))
    except Exception as exc:  # pragma: no cover - log and re-raise
        raise RuntimeError(f"Failed to load R-CNN model weights from {weights_path}: {exc}")
    model.to(device)
    model.eval()
    
    # Only detect batch size if requested (e.g., when adding model to DB)
    if detect_batch_size:
        optimal_bs = _detect_optimal_batch_size(model, "rcnn", device)
        return model, device, optimal_bs
    
    # For inference, use provided batch size from database
    return model, device, optimal_batch_size


def load_yolo_model(weights_path: str, detect_batch_size: bool = False, optimal_batch_size: int = None):
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
    
    # Only detect batch size if requested (e.g., when adding model to DB)
    if detect_batch_size:
        optimal_bs = _detect_optimal_batch_size(model, "yolo", device)
        return model, device, optimal_bs
    
    # For inference, use provided batch size from database
    return model, device, optimal_batch_size


def load_ssd_model(weights_path: str):  # pragma: no cover - placeholder
    raise NotImplementedError("SSD model loading not implemented.")


def load_cnn_model(weights_path: str):  # pragma: no cover - placeholder
    raise NotImplementedError("CNN detection model loading not implemented.")


def load_model(weights_path: str, model_type: str, detect_batch_size: bool = False, optimal_batch_size: int = None):
    """Load model and optionally detect optimal batch size.
    
    Args:
        weights_path: Path to model weights
        model_type: Type of model (RCNN, YOLO, etc.)
        detect_batch_size: If True, run batch size detection (slow, do once when adding model)
        optimal_batch_size: Pre-detected optimal batch size from database (for inference)
        
    Returns:
        Tuple of (model, device, optimal_batch_size)
    """
    model_type_lower = model_type.lower()
    if "rcnn" in model_type_lower or "faster" in model_type_lower:
        return load_rcnn_model(weights_path, detect_batch_size, optimal_batch_size)
    if "yolo" in model_type_lower:
        return load_yolo_model(weights_path, detect_batch_size, optimal_batch_size)
    if "ssd" in model_type_lower:
        return load_ssd_model(weights_path)
    if "cnn" in model_type_lower and "rcnn" not in model_type_lower:
        return load_cnn_model(weights_path)
    raise ValueError(
        f"Unsupported model type: {model_type}. Supported types: RCNN, YOLO, SSD, CNN."
    )


"""
Model loading utilities for PyTorch object detection models.

This module handles:
- Loading supported model types (FASTRCNN, YOLO)
- Applying inference optimizations
- Device selection (GPU if available, otherwise CPU)
"""

import torch
from torchvision.models.detection import fasterrcnn_resnet50_fpn

SUPPORTED_MODEL_TYPES = ("FASTRCNN", "YOLO")


def _load_checkpoint(weights_path: str, device: torch.device):
    """
    Load model checkpoint file and extract the actual model weights.
    
    Checkpoint files can be saved in different formats:
    1. Direct state dict: Just the model weights
    2. Full training checkpoint: Includes model weights, optimizer state, etc.
    
    This function handles both formats automatically.
    
    Args:
        weights_path: Path to the .pt or .pth file
        device: Device to load the model on (cpu, cuda, or mps)
        
    Returns:
        The model state dict (weights)
    """
    # Load the checkpoint file
    # map_location ensures it loads on the correct device (CPU/GPU)
    checkpoint = torch.load(weights_path, map_location=device)
    
    # If checkpoint is a dictionary, extract the actual model weights
    if isinstance(checkpoint, dict):
        # Try common keys where model weights are stored
        for key in ("model_state_dict", "state_dict"):
            if key in checkpoint:
                return checkpoint[key]
    
    # If checkpoint is already the state dict, return it directly
    return checkpoint


def load_rcnn_model(weights_path: str):
    """
    Load a Faster R-CNN model for mussel detection.

    Args:
        weights_path: Path to the .pth file with trained weights

    Returns:
        Tuple of (model, device)
    """

    # Determine which device to use (GPU is faster if available)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 3 classes: background, live mussel, dead mussel.
    model = fasterrcnn_resnet50_fpn(weights=None, weights_backbone=None, num_classes=3)

    # Load the trained weights from file
    try:
        model.load_state_dict(_load_checkpoint(weights_path, device))
    except Exception as exc:
        raise RuntimeError(f"Failed to load R-CNN model weights from {weights_path}: {exc}")

    # Move model to the chosen device (CPU or GPU)
    model.to(device)

    # Set to evaluation mode (disables dropout, batch norm training, etc.)
    model.eval()

    # Apply inference optimizations
    # These make inference faster without affecting results
    torch.set_grad_enabled(False)  # Don't track gradients (only needed for training)
    if device.type == "cpu":
        # On CPU, disable CUDA backend to reduce overhead
        torch.backends.cudnn.enabled = False

    return model, device


def load_yolo_model(weights_path: str):
    """
    Load a YOLO model for mussel detection.

    Args:
        weights_path: Path to the .pt file with YOLO weights

    Returns:
        Tuple of (model, device)
    """

    # Try to import YOLO library
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise ImportError("ultralytics not installed. Install it with: pip install ultralytics") from exc
    
    # Determine which device to use (GPU is faster if available)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load the YOLO model from file
    model = YOLO(weights_path)

    # Try to apply layer fusing optimization
    # This combines layers to make inference faster
    if hasattr(model, "model") and hasattr(model.model, "fuse"):
        original_fuse = model.model.fuse
        
        def safe_fuse(*args, **kwargs):
            """
            Wrapper for layer fusing that handles PyTorch compatibility issues.
            Some PyTorch versions have a bug where Conv layers don't have 'bn' attribute.
            """
            try:
                return original_fuse(*args, **kwargs)
            except AttributeError as exc:
                # Known PyTorch compatibility issue
                if "'Conv' object has no attribute 'bn'" in str(exc):
                    return model.model
                # Re-raise unexpected errors
                raise
        
        # Replace the fuse method with our safe version
        model.model.fuse = safe_fuse
    
    # Move model to the chosen device (CPU or GPU)
    if hasattr(model.model, "to"):
        model.model.to(device)

    # Set to evaluation mode
    model.model.eval()

    # Apply inference optimizations
    torch.set_grad_enabled(False)  # Don't track gradients (only needed for training)
    if device.type == "cpu":
        # On CPU, disable CUDA backend to reduce overhead
        torch.backends.cudnn.enabled = False

    return model, device


def load_model(weights_path: str, model_type: str):
    """
    Main entry point for loading any supported model type.
    
    This function routes by canonical SQL model type.
    
    Supported Model Types:
    - "FASTRCNN" → loads Faster R-CNN
    - "YOLO" → loads YOLO
    
    What Gets Returned:
    - model: The loaded PyTorch model ready for inference
    - device: Which device it's on (cpu, cuda, or mps)
    
    Args:
        weights_path: Path to the .pt or .pth file with model weights
        model_type: Canonical model type (e.g., "YOLO", "FASTRCNN")
        
    Returns:
        Tuple of (model, device)
        
    Raises:
        ValueError: If model_type is not supported
        
    Example:
        model, device = load_model("yolov8n.pt", "YOLO")
        # Returns: (YOLO model, "cpu")
    """
    if model_type == "FASTRCNN":
        return load_rcnn_model(weights_path)
    if model_type == "YOLO":
        return load_yolo_model(weights_path)

    raise ValueError(
        f"Unsupported model type: {model_type}. "
        f"Supported types: {', '.join(SUPPORTED_MODEL_TYPES)}."
    )

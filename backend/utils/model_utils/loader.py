"""
Model loading utilities for PyTorch object detection models.

This module handles:
- Loading different model types (R-CNN, YOLO)
- Detecting optimal batch sizes based on model parameter count
- Applying inference optimizations (gradient disabling, CPU tuning)
- Device selection (GPU if available, otherwise CPU)
"""

import torch
from torchvision.models.detection import fasterrcnn_resnet50_fpn


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


def load_rcnn_model(weights_path: str, model_type: str):
    """
    Load a Faster R-CNN model for mussel detection.
    
    What is Faster R-CNN?
    - Object detection model that finds objects in images
    - Uses ResNet50 as the "backbone" (feature extractor)
    - FPN (Feature Pyramid Network) helps detect objects at different sizes
    - Slower than YOLO but often more accurate
    
    What This Function Does:
    1. Choose GPU if available, otherwise use CPU
    2. Create the model architecture (ResNet50-FPN backbone, 3 classes)
    3. Load the trained weights from file
    4. Put model in "eval" mode (turns off training features)
    5. Apply optimizations to make inference faster
    6. Calculate optimal batch size based on model size
    
    The 3 Classes:
    - Background (not a mussel)
    - Live mussel
    - Dead mussel
    
    Args:
        weights_path: Path to the .pth file with trained weights
        model_type: Type string (e.g., "Faster R-CNN")
        
    Returns:
        Tuple of (model, device, batch_size)
    """
    
    # Determine which device to use (GPU is faster if available)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Create the model architecture
    # pretrained=False: Don't use ImageNet weights, we have custom weights
    # num_classes=3: Background, live mussel, dead mussel
    model = fasterrcnn_resnet50_fpn(pretrained=False, weights_backbone=None, num_classes=3)
    
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
    if device.type == 'cpu':
        # On CPU, disable CUDA backend to reduce overhead
        torch.backends.cudnn.enabled = False
    
    # Fixed batch size for CPU-only use
    batch_size = 1
    
    return model, device, batch_size


def load_yolo_model(weights_path: str, model_type: str):
    """
    Load a YOLO model for mussel detection.
    
    What is YOLO?
    - "You Only Look Once" - very fast object detection model
    - Processes entire image in one pass (unlike R-CNN which processes regions)
    - Comes in different sizes: nano (n), small (s), medium (m), large (l), xlarge (x)
    - Generally faster than R-CNN but may be less accurate
    
    What This Function Does:
    1. Import YOLO from ultralytics library
    2. Choose GPU if available, otherwise use CPU
    3. Load the YOLO model from weights file
    4. Apply "layer fusing" optimization (makes inference faster)
    5. Put model in eval mode and apply optimizations
    6. Calculate optimal batch size
    
    Layer Fusing:
    - Combines Conv+BatchNorm+Activation into single operation
    - Makes inference faster without changing results
    - Sometimes fails due to PyTorch version issues (handled gracefully)
    
    Args:
        weights_path: Path to the .pt file with YOLO weights
        model_type: Type string (e.g., "YOLO")
        
    Returns:
        Tuple of (model, device, batch_size)
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
    if device.type == 'cpu':
        # On CPU, disable CUDA backend to reduce overhead
        torch.backends.cudnn.enabled = False
    
    # Fixed batch size for CPU-only use
    batch_size = 2
    
    return model, device, batch_size


def load_ssd_model(weights_path: str):  # pragma: no cover - placeholder
    raise NotImplementedError("SSD model loading not implemented.")


def load_cnn_model(weights_path: str):  # pragma: no cover - placeholder
    raise NotImplementedError("CNN detection model loading not implemented.")


def load_model(weights_path: str, model_type: str):
    """
    Main entry point for loading any supported model type.
    
    This function acts as a router - it looks at the model_type string
    and calls the appropriate specific loader (R-CNN, YOLO, etc.).
    
    Supported Model Types:
    - "Faster R-CNN", "RCNN" → loads Faster R-CNN
    - "YOLO", "YOLOv8" → loads YOLO
    - "SSD" → not implemented yet
    - "CNN" → not implemented yet
    
    What Gets Returned:
    - model: The loaded PyTorch model ready for inference
    - device: Which device it's on (cpu, cuda, or mps)
    - batch_size: How many images to process at once
    
    Args:
        weights_path: Path to the .pt or .pth file with model weights
        model_type: Type of model as a string (e.g., "YOLO", "Faster R-CNN")
        
    Returns:
        Tuple of (model, device, batch_size)
        
    Raises:
        ValueError: If model_type is not supported
        
    Example:
        model, device, batch_size = load_model("yolov8n.pt", "YOLO")
        # Returns: (YOLO model, "cpu", 4)
    """
    # Convert to lowercase for case-insensitive matching
    model_type_lower = model_type.lower()
    
    # Route to appropriate loader based on model type
    if "rcnn" in model_type_lower or "faster" in model_type_lower:
        return load_rcnn_model(weights_path, model_type)
    if "yolo" in model_type_lower:
        return load_yolo_model(weights_path, model_type)
    if "ssd" in model_type_lower:
        return load_ssd_model(weights_path)
    if "cnn" in model_type_lower and "rcnn" not in model_type_lower:
        return load_cnn_model(weights_path)
    
    # Model type not recognized
    raise ValueError(
        f"Unsupported model type: {model_type}. Supported types: RCNN, YOLO, SSD, CNN."
    )

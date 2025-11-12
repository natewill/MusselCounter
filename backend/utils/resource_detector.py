import os
import torch
from utils.logger import logger


def pick_threads():
    """Optimize CPU threading for PyTorch. Only matters on CPU; GPU/MPS returns None."""
    if torch.cuda.is_available():
        logger.debug("[Resource Detection] CUDA available, skipping CPU thread optimization")
        return None
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        logger.debug("[Resource Detection] MPS available, skipping CPU thread optimization")
        return None
    
    cpu_count = os.cpu_count() or 4
    t = max(1, cpu_count // 3)  # Less aggressive threading to reduce CPU contention
    logger.debug(f"[Resource Detection] CPU mode detected: {cpu_count} cores available, setting {t} threads")
    torch.set_num_threads(t)
    torch.set_num_interop_threads(1)
    os.environ["OMP_NUM_THREADS"] = str(t)
    return t


def calculate_batch_size_from_model(model, device: torch.device) -> int:
    """
    Calculate optimal batch size based on actual model parameter count and available memory.
    
    This is much more accurate than using model type strings, as it accounts for:
    - YOLOv8n (3MB, 3.2M params) vs YOLOv8x (136MB, 68M params)
    - Different R-CNN backbones (ResNet18 vs ResNet50 vs ResNet101)
    - Custom models of varying sizes
    
    Args:
        model: The loaded PyTorch model
        device: Device the model is on (cpu, cuda, mps)
        
    Returns:
        Optimal batch size for the given model and device
    """
    # Count total parameters in the model
    param_count = sum(p.numel() for p in model.parameters())
    param_mb = (param_count * 4) / (1024 * 1024)  # 4 bytes per float32 parameter
    
    logger.info(f"[Resource Detection] Model size: {param_count:,} parameters ({param_mb:.1f} MB)")
    
    # Define memory tiers based on model size
    # Small: < 10M params (e.g., YOLOv8n, MobileNet)
    # Medium: 10M - 30M params (e.g., YOLOv8s, ResNet50)
    # Large: 30M - 60M params (e.g., YOLOv8m, ResNet101)
    # XLarge: > 60M params (e.g., YOLOv8x, larger R-CNNs)
    
    if torch.cuda.is_available():
        # GPU - much more memory available
        if param_count < 10_000_000:  # < 10M params
            batch_size = 32
        elif param_count < 30_000_000:  # 10-30M params
            batch_size = 16
        elif param_count < 60_000_000:  # 30-60M params
            batch_size = 8
        else:  # > 60M params
            batch_size = 4
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        # Apple Silicon - moderate memory
        if param_count < 10_000_000:
            batch_size = 16
        elif param_count < 30_000_000:
            batch_size = 8
        elif param_count < 60_000_000:
            batch_size = 4
        else:
            batch_size = 2
    else:
        # CPU - limited memory, conservative approach
        if param_count < 10_000_000:
            batch_size = 4
        elif param_count < 30_000_000:
            batch_size = 2
        elif param_count < 60_000_000:
            batch_size = 1
        else:
            batch_size = 1
    
    logger.info(f"[Resource Detection] Calculated batch size: {batch_size} for {param_count:,} params on {device.type}")
    return batch_size

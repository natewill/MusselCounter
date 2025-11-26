import os
import torch


def pick_threads():
    """
    Optimize PyTorch's CPU threading to reduce system lag during inference.
    
    The Problem:
    - PyTorch defaults to using ALL CPU cores, which causes high system load
    - This makes the UI freeze/lag during inference runs
    - Too many threads causes "thrashing" where cores compete for resources
    
    The Solution:
    - Only run on CPU (GPU/MPS don't need this optimization)
    - Use cpu_count // 3 threads (roughly the number of physical cores)
    - Set interop threads to 1 (prevents thread pool contention)
    - Configure OpenMP to respect the same limit
    
    Example:
    - 12 CPU cores → Use 4 threads (smoother, less lag)
    - 8 CPU cores → Use 2 threads
    
    Returns:
        int: Number of threads configured, or None if GPU/MPS is being used
    """
    # Skip optimization if using GPU (NVIDIA CUDA)
    if torch.cuda.is_available():
        return None
    
    # Skip optimization if using Apple Silicon GPU (Metal Performance Shaders)
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return None
    
    # Get CPU core count (fallback to 4 if detection fails)
    cpu_count = os.cpu_count() or 4
    
    # Use 1/3 of cores - less aggressive to prevent system overload
    # max(1, ...) ensures at least 1 thread even on single-core systems
    t = max(1, cpu_count // 3)
    
    # Configure PyTorch threading
    torch.set_num_threads(t)          # Main operation threads
    torch.set_num_interop_threads(1)  # Single thread for inter-operation parallelism
    
    # Configure OpenMP (used by math libraries like MKL)
    os.environ["OMP_NUM_THREADS"] = str(t)
    
    return t


def calculate_batch_size_from_model(model, device: torch.device) -> int:
    """
    Calculate optimal batch size based on how big the model actually is.
    
    Why This Matters:
    - Small models (YOLOv8n = 3MB) can process many images at once
    - Large models (YOLOv8x = 136MB) need to process fewer images at a time
    - Using the wrong batch size causes:
      * Too small → Slow inference (not using full CPU/GPU)
      * Too large → Out of memory crashes
    
    How It Works:
    1. Count how many parameters (weights) the model has
    2. Categorize model into size tier (small/medium/large/xlarge)
    3. Assign batch size based on tier and available hardware (GPU/CPU)
    
    Model Size Tiers:
    - Small (<10M params): YOLOv8n, MobileNet
    - Medium (10-30M): YOLOv8s, Faster R-CNN ResNet50
    - Large (30-60M): YOLOv8m, ResNet101
    - XLarge (>60M): YOLOv8x, very large R-CNNs
    
    Args:
        model: The loaded PyTorch model
        device: Device the model is running on (cpu, cuda, or mps)
        
    Returns:
        int: Optimal batch size (number of images to process at once)
        
    Example:
        YOLOv8n (3.2M params) on CPU → batch_size = 4 (fast processing)
        Faster R-CNN (25M params) on CPU → batch_size = 2 (balanced)
        YOLOv8x (68M params) on CPU → batch_size = 1 (avoid memory issues)
    """
    # Count total parameters in the model
    # Each parameter is a float32 (4 bytes)
    param_count = sum(p.numel() for p in model.parameters())
    param_mb = (param_count * 4) / (1024 * 1024)  # Convert to megabytes
    
    # Determine batch size based on device type and model size
    # GPU has most memory, Apple Silicon (MPS) is middle, CPU has least
    
    if torch.cuda.is_available():
        # GPU - much more memory available, can handle larger batches
        if param_count < 10_000_000:  # Small model
            batch_size = 32
        elif param_count < 30_000_000:  # Medium model
            batch_size = 16
        elif param_count < 60_000_000:  # Large model
            batch_size = 8
        else:  # XLarge model
            batch_size = 4
            
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        # Apple Silicon GPU - moderate memory, middle ground
        if param_count < 10_000_000:
            batch_size = 16
        elif param_count < 30_000_000:
            batch_size = 8
        elif param_count < 60_000_000:
            batch_size = 4
        else:
            batch_size = 2
            
    else:
        # CPU - limited memory, must be conservative
        # Also slower, so smaller batches are actually better
        if param_count < 10_000_000:
            batch_size = 4
        elif param_count < 30_000_000:
            batch_size = 2
        elif param_count < 60_000_000:
            batch_size = 1
        else:
            batch_size = 1
    
    return batch_size

"""
Inference routing and adapter registry.

This module is the central dispatcher for model inference.
It maps canonical SQL model types (e.g., FASTRCNN, YOLO) to
adapter functions that return the shared application result format.

Why this exists:
- Keeps model-specific branching in one place
- Lets the rest of the pipeline call one stable API
- Makes future model additions a registry change instead of a broad refactor
"""

from typing import Callable
from .rcnn import run_rcnn_inference, run_rcnn_inference_batch
from .yolo import run_yolo_inference, run_yolo_inference_batch


def run_ssd_inference(model_device_tuple, image_path: str):
    """
    SSD (Single Shot Detector) inference placeholder.

    Raises:
        NotImplementedError: SSD adapter has not been implemented yet.
    """
    raise NotImplementedError("SSD inference not implemented.")


def run_cnn_inference(model_device_tuple, image_path: str):
    """
    Generic CNN object-detection inference placeholder.

    Raises:
        NotImplementedError: CNN adapter has not been implemented yet.
    """
    raise NotImplementedError("CNN detection inference not implemented.")


def _get_inference_adapter(model_type: str, batch: bool) -> Callable:
    """
    Retrieve the adapter for an exact model type and execution mode.

    Args:
        model_type: Canonical model type string from SQL (e.g., "YOLO", "FASTRCNN")
        batch: True for batch adapter, False for single-image adapter

    Returns:
        Callable adapter function for the requested model type and mode.

    Raises:
        ValueError: If model_type is unknown or does not support the requested mode.
    """
    mode = "batch" if batch else "single"
    model_adapters = INFERENCE_ADAPTERS.get(model_type)

    if model_adapters is None:
        supported = ", ".join(INFERENCE_ADAPTERS.keys())
        raise ValueError(
            f"Unsupported model type: {model_type}. Supported types: {supported}."
        )

    adapter = model_adapters.get(mode)
    if adapter is None:
        execution_mode = "batch" if batch else "single-image"
        raise ValueError(
            f"Model type '{model_type}' does not support {execution_mode} inference."
        )

    return adapter


def supports_batch_inference(model_type: str) -> bool:
    """
    Check whether a model type has a registered batch adapter.

    Args:
        model_type: Canonical model type string from SQL.

    Returns:
        True if a batch adapter exists for the model type, otherwise False.

    Raises:
        ValueError: If model_type is unknown.
    """
    model_adapters = INFERENCE_ADAPTERS.get(model_type)
    if model_adapters is None:
        supported = ", ".join(INFERENCE_ADAPTERS.keys())
        raise ValueError(
            f"Unsupported model type: {model_type}. Supported types: {supported}."
        )
    return "batch" in model_adapters


def run_inference_batch(model_device_tuple, image_paths: list[str], model_type: str):
    """
    Main entry point for running inference on multiple images.

    This function routes to the registered batch adapter for the model type.

    Args:
        model_device_tuple: (model, device, batch_size) from model loader
        image_paths: List of image file paths
        model_type: Canonical model type string from SQL

    Returns:
        List of standardized result dicts, one per input image.

    Raises:
        ValueError: If model_type is unsupported or has no batch adapter.
    """
    adapter = _get_inference_adapter(model_type, batch=True)
    return adapter(model_device_tuple, image_paths)


def run_inference_on_image(model_device_tuple, image_path: str, model_type: str):
    """
    Main entry point for running inference on a single image.

    This function routes to the registered single-image adapter for the model type.

    Args:
        model_device_tuple: (model, device, batch_size) from model loader
        image_path: Path to one image file
        model_type: Canonical model type string from SQL

    Returns:
        Standardized inference result dict with:
        - live_count
        - dead_count
        - polygons

    Raises:
        ValueError: If model_type is unsupported or has no single-image adapter.
    """
    adapter = _get_inference_adapter(model_type, batch=False)
    return adapter(model_device_tuple, image_path)


# Adapter registry by canonical SQL model type.
# Each entry maps execution mode to a model-specific adapter function.
INFERENCE_ADAPTERS: dict[str, dict[str, Callable]] = {
    "FASTRCNN": {
        "single": run_rcnn_inference,
        "batch": run_rcnn_inference_batch,
    },
    "YOLO": {
        "single": run_yolo_inference,
        "batch": run_yolo_inference_batch,
    },
}

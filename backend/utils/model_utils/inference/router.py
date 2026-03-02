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
from .rcnn import run_rcnn_inference
from .yolo import run_yolo_inference


def _get_inference_adapter(model_type: str) -> Callable:
    """
    Retrieve the single-image adapter for an exact model type.

    Args:
        model_type: Canonical model type string from SQL (e.g., "YOLO", "FASTRCNN")

    Returns:
        Callable adapter function for the requested model type.

    Raises:
        ValueError: If model_type is unknown.
    """
    adapter = INFERENCE_ADAPTERS.get(model_type)
    if adapter is None:
        supported = ", ".join(INFERENCE_ADAPTERS.keys())
        raise ValueError(
            f"Unsupported model type: {model_type}. Supported types: {supported}."
        )
    return adapter


def run_inference_on_image(model_device_tuple, image_path: str, model_type: str):
    """
    Main entry point for running inference on a single image.

    This function routes to the registered single-image adapter for the model type.

    Args:
        model_device_tuple: (model, device) from model loader
        image_path: Path to one image file
        model_type: Canonical model type string from SQL

    Returns:
        Standardized inference result dict with:
        - live_count
        - dead_count
        - polygons

    Raises:
        ValueError: If model_type is unsupported.
    """
    adapter = _get_inference_adapter(model_type)
    return adapter(model_device_tuple, image_path)


# Adapter registry by canonical SQL model type.
# Each entry maps directly to a single-image model adapter function.
INFERENCE_ADAPTERS: dict[str, Callable] = {
    "FASTRCNN": run_rcnn_inference,
    "YOLO": run_yolo_inference,
}

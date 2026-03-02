"""
Compatibility facade for inference APIs.

The implementation is split across:
- common.py
- rcnn.py
- yolo.py
- router.py
"""

from .rcnn import run_rcnn_inference
from .router import (
    INFERENCE_ADAPTERS,
    run_inference_on_image,
)
from .yolo import run_yolo_inference

__all__ = [
    "run_rcnn_inference",
    "run_yolo_inference",
    "run_inference_on_image",
    "INFERENCE_ADAPTERS",
]

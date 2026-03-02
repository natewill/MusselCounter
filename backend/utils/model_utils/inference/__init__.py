"""
Compatibility facade for inference APIs.

The implementation is split across:
- common.py
- rcnn.py
- yolo.py
- router.py
"""

from .rcnn import run_rcnn_inference, run_rcnn_inference_batch
from .router import (
    INFERENCE_ADAPTERS,
    run_cnn_inference,
    run_inference_batch,
    run_inference_on_image,
    run_ssd_inference,
    supports_batch_inference,
)
from .yolo import run_yolo_inference, run_yolo_inference_batch

__all__ = [
    "run_rcnn_inference",
    "run_rcnn_inference_batch",
    "run_yolo_inference",
    "run_yolo_inference_batch",
    "run_ssd_inference",
    "run_cnn_inference",
    "supports_batch_inference",
    "run_inference_batch",
    "run_inference_on_image",
    "INFERENCE_ADAPTERS",
]

"""Compatibility shim for legacy imports.

The codebase renamed batch processing to collections. This module keeps old
imports (`utils.run_utils.batch_processor`) working by forwarding to the new
implementation.
"""
from .collection_processor import process_collection_run as process_batch_run

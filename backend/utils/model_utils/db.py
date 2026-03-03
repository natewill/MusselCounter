from pathlib import Path

from config import MODELS_DIR

_MODEL_EXTENSIONS = {'.pt', '.pth', '.ckpt'}


def _infer_model_type(file_name: str) -> str:
    name = file_name.lower()
    if 'yolo' in name:
        return 'YOLO'
    if 'faster' in name or 'rcnn' in name or 'cnn' in name:
        return 'FASTRCNN'
    return 'YOLO'


def _build_model_rows() -> list[dict]:
    model_files = [
        p for p in MODELS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in _MODEL_EXTENSIONS
    ]
    model_files.sort(key=lambda p: p.name.lower())

    rows = []
    for idx, model_file in enumerate(model_files, start=1):
        rows.append(
            {
                'model_id': idx,
                'name': model_file.stem,
                'type': _infer_model_type(model_file.name),
                'weights_path': str(model_file),
            }
        )
    return rows


async def get_all_models(_db=None):
    """
    Return available models from backend/data/models.
    """
    return _build_model_rows()


async def get_model(_db=None, model_id: int = 0):
    """
    Return one model by derived model_id.
    """
    for row in _build_model_rows():
        if int(row['model_id']) == int(model_id):
            return row
    return None

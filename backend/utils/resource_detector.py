import torch
import logging
from accelerate.utils import find_executable_batch_size


def auto_bs(model, make_input, start=64, device=None):
    """Return the largest batch size that fits a forward pass.

    - model: nn.Module
    - make_input: callable(bs) -> Tensor or list[Tensor] (whatever your model expects)
    """
    dev = torch.device(device) if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval().to(dev)
    
    # Suppress model output during batch size detection
    # YOLO models print detection results even with verbose=False
    original_level = logging.getLogger().level
    logging.getLogger().setLevel(logging.ERROR)

    @find_executable_batch_size(starting_batch_size=start)
    def _probe(bs: int) -> int:
        x = make_input(bs)
        if isinstance(x, torch.Tensor):
            x = x.to(dev, non_blocking=True)
        else:  # list/tuple for RCNN-style models
            x = [t.to(dev, non_blocking=True) for t in x]
        with torch.inference_mode():
            _ = model(x, verbose=False)  # Suppress YOLO output
        return bs  # means "this bs works"

    result = _probe()
    logging.getLogger().setLevel(original_level)  # Restore logging
    return result


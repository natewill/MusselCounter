"""
Shared inference helpers and label mappings.
"""

# Label mappings - different models use different class numbers
# R-CNN: 0=background, 1=live, 2=dead
# YOLO: 0=live, 1=dead (no background class)
RCNN_LABELS = {1: "live", 2: "dead"}
YOLO_LABELS = {0: "live", 1: "dead"}


def convert_to_dictionary(live, dead, polygons):
    """
    Create standardized inference result dict.
    """
    return {
        "live_count": live,
        "dead_count": dead,
        "polygons": polygons,
    }

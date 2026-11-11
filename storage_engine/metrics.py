"""storage-side metrics."""

def calculate_utilization(inventory: dict) -> float:
    """Calculate the percentage of boxes currently occupied."""
    boxes = inventory.get("boxes", [])
    total_boxes = inventory.get("box_count", len(boxes))
    if total_boxes == 0:
        return 0.0

    occupied_count = sum(1 for b in boxes if b.get("occupied", False))
    return round((occupied_count / total_boxes) * 100.0, 2)


def calculate_internal_fragmentation(inventory: dict) -> int:
    """Calculate total unused capacity inside occupied boxes."""
    boxes = inventory.get("boxes", [])
    box_capacity = inventory.get("box_capacity", 100)
    total_wasted = 0

    for b in boxes:
        if b.get("occupied", False):
            used = b.get("used_size", box_capacity)
            total_wasted += max(0, box_capacity - used)

    return total_wasted
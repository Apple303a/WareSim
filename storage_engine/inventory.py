"""Warehouse box inventory and free-space tracking."""

def create_inventory(box_count: int, box_capacity: int) -> dict:
    """Create zero-based boxes; one box can hold one block."""
    boxes = [
        {
            "box_id": i,
            "position": i,
            "capacity": box_capacity,
            "occupied": False,
            "block_id": None,
            "shipment_id": None
        }
        for i in range(box_count)
    ]
    return {
        "box_count": box_count,
        "box_capacity": box_capacity,
        "boxes": boxes
    }


def get_shipment_positions(shipment_id: str, allocation_metadata: dict) -> list[int]:
    """Return physical positions for all blocks of a shipment."""
    allocated_blocks = allocation_metadata.get("allocated_blocks", [])
    positions = []
    for blk in allocated_blocks:
        if "position" in blk:
            positions.append(blk["position"])
    return positions


def calculate_storage_metrics(inventory: dict) -> dict:
    """Return utilization and internal-fragmentation metrics."""
    boxes = inventory.get("boxes", [])
    total_boxes = inventory.get("box_count", len(boxes))
    box_capacity = inventory.get("box_capacity", 100)

    occupied_boxes = sum(1 for b in boxes if b.get("occupied", False))
    utilization = (occupied_boxes / total_boxes * 100) if total_boxes > 0 else 0.0

    total_unused_capacity = 0
    for b in boxes:
        if b.get("occupied", False):
            used = b.get("used_size", box_capacity)
            total_unused_capacity += max(0, box_capacity - used)

    return {
        "total_boxes": total_boxes,
        "occupied_boxes": occupied_boxes,
        "free_boxes": total_boxes - occupied_boxes,
        "storage_utilization_pct": round(utilization, 2),
        "internal_fragmentation_units": total_unused_capacity
    }
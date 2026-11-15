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
    """Return utilization and internal/external fragmentation metrics.

    External fragmentation is measured as free boxes outside the largest
    contiguous free extent. This is a textbook contiguous-allocation measure.
    """
    boxes = inventory.get("boxes", [])
    total_boxes = inventory.get("box_count", len(boxes))
    box_capacity = inventory.get("box_capacity", 100)

    occupied_boxes = sum(1 for b in boxes if b.get("occupied", False))
    utilization = (occupied_boxes / total_boxes * 100) if total_boxes > 0 else 0.0
    largest_free_extent = 0
    current_free_extent = 0
    for box in boxes:
        if box.get("occupied", False):
            current_free_extent = 0
        else:
            current_free_extent += 1
            largest_free_extent = max(largest_free_extent, current_free_extent)
    free_boxes = total_boxes - occupied_boxes
    external_fragmentation_units = free_boxes - largest_free_extent
    external_fragmentation_pct = (
        external_fragmentation_units / free_boxes * 100 if free_boxes else 0.0
    )

    total_unused_capacity = 0
    for b in boxes:
        if b.get("occupied", False):
            used = b.get("used_size", box_capacity)
            total_unused_capacity += max(0, box_capacity - used)

    return {
        "total_boxes": total_boxes,
        "occupied_boxes": occupied_boxes,
        "free_boxes": free_boxes,
        "storage_utilization_pct": round(utilization, 2),
        "internal_fragmentation_units": total_unused_capacity,
        "largest_free_extent": largest_free_extent,
        "external_fragmentation_units": external_fragmentation_units,
        "external_fragmentation_pct": round(external_fragmentation_pct, 2),
    }
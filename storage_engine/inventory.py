"""Warehouse box inventory and free-space tracking."""

def create_inventory(box_count: int, box_capacity: int) -> dict:
    """Create zero-based boxes; one box can hold one block."""
    raise NotImplementedError


def get_shipment_positions(shipment_id: str, allocation_metadata: dict) -> list[int]:
    """Return physical positions for all blocks of a shipment."""
    raise NotImplementedError


def calculate_storage_metrics(inventory: dict) -> dict:
    """Return utilization and internal-fragmentation metrics."""
    raise NotImplementedError

"""Contiguous, linked and indexed allocation."""

def allocate_blocks(blocks: dict, inventory: dict, algorithm: str) -> dict:
    """Allocate blocks and return allocation metadata plus updated inventory.

    Every allocated block must expose block_id, box_id and integer position.
    """
    raise NotImplementedError


def deallocate_shipment(shipment_id: str, allocation_metadata: dict, inventory: dict) -> dict:
    """Free every box belonging to the shipment and return updated state."""
    raise NotImplementedError


def resize_shipment(shipment_id: str, new_size: int, block_size: int,
                    allocation_metadata: dict, inventory: dict) -> dict:
    """Preserve existing blocks where possible; allocate/free only the difference."""
    raise NotImplementedError

"""Split shipment sizes into fixed-size blocks."""
import math

def generate_blocks(shipment: dict, block_size: int) -> dict:
    """
    Return {shipment_id, block_size, blocks[]}.
    Block count = ceil(shipment size / block_size).
    Each block has block_id, block_index and used_size.
    """
    shipment_id = shipment["shipment_id"]
    size = shipment["size"]

    if size <= 0:
        raise ValueError("Shipment size must be positive")

    num_blocks = math.ceil(size / block_size)
    blocks = []
    remaining_size = size

    for i in range(num_blocks):
        current_used = min(remaining_size, block_size)
        blocks.append({
            "block_id": f"{shipment_id}_B{i+1}",
            "block_index": i,
            "used_size": current_used
        })
        remaining_size -= current_used

    return {
        "shipment_id": shipment_id,
        "block_size": block_size,
        "blocks": blocks
    }

"""Split shipment sizes into fixed-size blocks."""

def generate_blocks(shipment: dict, block_size: int) -> dict:
    """Return {shipment_id, block_size, blocks[]}.

    Block count = ceil(shipment size / block size).
    Each block has block_id, block_index and used_size.
    """
    raise NotImplementedError

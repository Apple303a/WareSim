"""Block-level I/O request queue."""

def validate_requests(requests: list[dict]) -> None:
    """Validate request IDs, operations, arrival times and integer positions."""
    raise NotImplementedError


def build_block_requests(shipment_id: str, block_records: list[dict],
                         operation: str, arrival_time: float = 0) -> list[dict]:
    """Create one request per block, using the block's physical position."""
    raise NotImplementedError

"""Shared data contracts.

Keep field names and meanings stable. Discuss changes with all team members
before changing these contracts.
"""

from typing import Any, TypedDict


class ShipmentInput(TypedDict):
    shipment_id: str
    name: str
    owner: str
    size: int


class Block(TypedDict):
    block_id: str
    block_index: int
    used_size: int


class AllocationRecord(TypedDict):
    block_id: str
    box_id: int
    position: int
    next_box: int | None


class OperationRequest(TypedDict):
    request_id: str
    shipment_id: str
    block_id: str
    operation: str  # READ or WRITE
    position: int
    arrival_time: float
    priority: int


# Suggested scheduler output keys:
# {
#   "algorithm": str,
#   "initial_position": int,
#   "execution_order": list[str],  # request IDs
#   "movement_path": list[int],    # includes initial position
#   "total_movement": int,
#   "metrics": {
#       "average_waiting_time": float,
#       "average_response_time": float,
#       "average_turnaround_time": float,
#       "throughput": float
#   }
# }

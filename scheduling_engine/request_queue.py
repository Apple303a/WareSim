"""Block-level I/O request construction and validation."""

import math
from numbers import Real

from shared.config import OPERATIONS


def validate_requests(requests: list[dict]) -> None:
    """Validate request fields, unique IDs, arrivals, operations, and positions."""
    if not isinstance(requests, list):
        raise ValueError("Requests must be a list.")

    required_fields = {
        "request_id",
        "shipment_id",
        "block_id",
        "operation",
        "position",
        "transfer_size",
        "arrival_time",
        "priority",
    }
    request_ids = set()

    for index, request in enumerate(requests):
        if not isinstance(request, dict):
            raise ValueError(f"Request at index {index} must be an object.")
        missing_fields = required_fields.difference(request)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"Request at index {index} is missing: {missing}.")

        request_id = request["request_id"]
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("Request IDs must be non-empty strings.")
        if request_id in request_ids:
            raise ValueError(f"Duplicate request ID: {request_id}")
        request_ids.add(request_id)

        for field in ("shipment_id", "block_id"):
            if not isinstance(request[field], str) or not request[field].strip():
                raise ValueError(f"{field} must be a non-empty string.")

        operation = request["operation"]
        if not isinstance(operation, str) or operation.upper() not in OPERATIONS:
            raise ValueError(
                f"Operation must be one of: {', '.join(OPERATIONS)}."
            )

        position = request["position"]
        if (
            not isinstance(position, int)
            or isinstance(position, bool)
            or position < 0
        ):
            raise ValueError("Request positions must be non-negative integers.")

        transfer_size = request["transfer_size"]
        if (
            not isinstance(transfer_size, Real)
            or isinstance(transfer_size, bool)
            or not math.isfinite(transfer_size)
            or transfer_size <= 0
        ):
            raise ValueError("Transfer sizes must be finite positive numbers.")

        arrival_time = request["arrival_time"]
        if (
            not isinstance(arrival_time, Real)
            or isinstance(arrival_time, bool)
            or not math.isfinite(arrival_time)
            or arrival_time < 0
        ):
            raise ValueError("Arrival times must be finite non-negative numbers.")

        priority = request["priority"]
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise ValueError("Request priority must be an integer.")


def build_block_requests(
    shipment_id: str,
    block_records: list[dict],
    operation: str,
    arrival_time: float = 0,
    operation_id: str = "1",
) -> list[dict]:
    """Create one validated scheduling request per allocated block."""
    if not isinstance(shipment_id, str) or not shipment_id.strip():
        raise ValueError("Shipment ID must be a non-empty string.")
    if not isinstance(operation, str) or operation.upper() not in OPERATIONS:
        raise ValueError(f"Operation must be one of: {', '.join(OPERATIONS)}.")
    if not isinstance(block_records, list):
        raise ValueError("Block records must be a list.")
    if not isinstance(operation_id, str) or not operation_id.strip():
        raise ValueError("Operation ID must be a non-empty string.")

    normalized_operation = operation.upper()
    requests = []
    for index, block in enumerate(block_records):
        if not isinstance(block, dict):
            raise ValueError(f"Block record at index {index} must be an object.")
        if "block_id" not in block or "position" not in block:
            raise ValueError(
                f"Block record at index {index} requires block_id and position."
            )
        block_id = block["block_id"]
        requests.append({
            "request_id": (
                f"{shipment_id}_{operation_id}_{normalized_operation}_{index + 1}"
            ),
            "shipment_id": shipment_id,
            "block_id": block_id,
            "operation": normalized_operation,
            "position": block["position"],
            "transfer_size": block.get("used_size", 100),
            "arrival_time": arrival_time,
            "priority": 1,
        })

    validate_requests(requests)
    return requests

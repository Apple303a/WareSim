"""Repeatable factorial experiments across storage and scheduling models."""

import math
import random
import uuid
from numbers import Real

from shared.config import (
    BLOCK_SIZE,
    BOX_COUNT,
    INITIAL_WORKER_POSITION,
    MAX_POSITION,
    MIN_POSITION,
    SCHEDULING_ALGORITHMS,
)
from scheduling_engine.algorithms import DEFAULT_TIMING, schedule_requests
from scheduling_engine.request_queue import build_block_requests
from storage_engine.allocation import allocate_blocks, deallocate_shipment
from storage_engine.block_generator import generate_blocks
from storage_engine.inventory import calculate_storage_metrics, create_inventory

ALLOCATION_ALGORITHMS = ("contiguous", "linked", "indexed")


def _integer(config: dict, key: str, minimum: int, maximum: int) -> int:
    value = config.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer.")
    if not minimum <= value <= maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}.")
    return value


def _positive_number(config: dict, key: str) -> float:
    value = config.get(key)
    if (
        not isinstance(value, Real)
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{key} must be a finite positive number.")
    return float(value)


def generate_workload(config: dict) -> dict:
    """Generate one deterministic workload shared by every experiment cell."""
    if not isinstance(config, dict):
        raise ValueError("Workload settings must be an object.")

    shipment_count = _integer(config, "shipment_count", 1, BOX_COUNT)
    replacement_count = _integer(config, "replacement_count", 0, BOX_COUNT)
    minimum_size = _integer(config, "minimum_size", 1, BLOCK_SIZE * BOX_COUNT)
    maximum_size = _integer(config, "maximum_size", minimum_size, BLOCK_SIZE * BOX_COUNT)
    operation_count = _integer(config, "operation_count", 1, 1000)
    read_percent = _integer(config, "read_percent", 0, 100)
    delete_percent = _integer(config, "delete_percent", 0, 90)
    seed = _integer(config, "seed", 0, 2**31 - 1)

    arrival_span = config.get("arrival_span", 0)
    if (
        not isinstance(arrival_span, Real)
        or isinstance(arrival_span, bool)
        or not math.isfinite(arrival_span)
        or arrival_span < 0
    ):
        raise ValueError("Arrival span must be a finite non-negative number.")

    timing = dict(DEFAULT_TIMING)
    supplied_timing = config.get("timing", {})
    if not isinstance(supplied_timing, dict):
        raise ValueError("Timing settings must be an object.")
    timing.update(supplied_timing)
    for key in DEFAULT_TIMING:
        _positive_number(timing, key)

    rng = random.Random(seed)
    shipments = []
    total_data_blocks = 0
    for index in range(shipment_count):
        size = rng.randint(minimum_size, maximum_size)
        total_data_blocks += math.ceil(size / BLOCK_SIZE)
        shipments.append({
            "shipment_id": f"SIM-{index + 1:03d}",
            "name": f"Simulated shipment {index + 1}",
            "owner": "WareSim",
            "size": size,
        })

    replacement_shipments = []
    replacement_data_blocks = 0
    for index in range(replacement_count):
        size = rng.randint(minimum_size, maximum_size)
        replacement_data_blocks += math.ceil(size / BLOCK_SIZE)
        replacement_shipments.append({
            "shipment_id": f"SIM-R{index + 1:03d}",
            "name": f"Replacement shipment {index + 1}",
            "owner": "WareSim",
            "size": size,
        })

    if total_data_blocks + shipment_count > BOX_COUNT:
        raise ValueError(
            "Generated shipments exceed capacity for indexed allocation. "
            "Reduce shipment count or size range."
        )
    if operation_count * math.ceil(maximum_size / BLOCK_SIZE) > 1000:
        raise ValueError(
            "The requested workload could create more than 1000 block-level "
            "I/O requests. Reduce operation count or maximum shipment size."
        )

    deleted_count = min(shipment_count - 1, shipment_count * delete_percent // 100)
    deleted_shipment_ids = rng.sample(
        [shipment["shipment_id"] for shipment in shipments], deleted_count
    )
    deleted_shipments = set(deleted_shipment_ids)
    active_shipments = [
        shipment for shipment in shipments
        if shipment["shipment_id"] not in deleted_shipments
    ]
    peak_indexed_usage = (
        total_data_blocks
        + shipment_count
        - sum(
            math.ceil(shipment["size"] / BLOCK_SIZE) + 1
            for shipment in shipments
            if shipment["shipment_id"] in deleted_shipments
        )
        + replacement_data_blocks
        + replacement_count
    )
    if peak_indexed_usage > BOX_COUNT:
        raise ValueError(
            "Generated replacement shipments exceed indexed warehouse capacity. "
            "Reduce replacement count or shipment size."
        )
    final_shipments = active_shipments + replacement_shipments

    read_count = round(operation_count * read_percent / 100)
    if 0 < read_percent < 100 and operation_count > 1:
        read_count = min(max(read_count, 1), operation_count - 1)
    operation_types = ["READ"] * read_count + [
        "WRITE"
    ] * (operation_count - read_count)
    rng.shuffle(operation_types)
    operations = []
    for index, operation in enumerate(operation_types):
        shipment = rng.choice(final_shipments)
        arrival_time = (
            round(rng.uniform(0, arrival_span), 2) if arrival_span else 0.0
        )
        operations.append({
            "operation_id": f"OP-{index + 1:04d}",
            "shipment_id": shipment["shipment_id"],
            "operation": operation,
            "arrival_time": arrival_time,
            "block_count": math.ceil(shipment["size"] / BLOCK_SIZE),
        })

    lifecycle_events = []

    def add_lifecycle_event(action: str, phase: str, shipment: dict, detail: str) -> None:
        lifecycle_events.append({
            "sequence": len(lifecycle_events) + 1,
            "action": action,
            "phase": phase,
            "shipment_id": shipment["shipment_id"],
            "name": shipment["name"],
            "size": shipment["size"],
            "detail": detail,
        })

    for shipment in shipments:
        add_lifecycle_event("CREATE", "Initial allocation", shipment, "Shipment added to the empty warehouse.")
    for shipment_id in deleted_shipment_ids:
        shipment = next(item for item in shipments if item["shipment_id"] == shipment_id)
        add_lifecycle_event("DELETE", "Deletion phase", shipment, "Shipment removed; its allocated boxes are freed.")
    for shipment in active_shipments:
        add_lifecycle_event("RETAIN", "Retention phase", shipment, "Shipment remains allocated after deletion.")
    for shipment in replacement_shipments:
        add_lifecycle_event("CREATE", "Replacement allocation", shipment, "New shipment added after deletions.")

    return {
        "workload_id": uuid.uuid4().hex,
        "config": {
            "shipment_count": shipment_count,
            "replacement_count": replacement_count,
            "minimum_size": minimum_size,
            "maximum_size": maximum_size,
            "operation_count": operation_count,
            "read_percent": read_percent,
            "delete_percent": delete_percent,
            "seed": seed,
            "arrival_span": float(arrival_span),
            "timing": timing,
        },
        "shipments": shipments,
        "replacement_shipments": replacement_shipments,
        "deleted_shipment_ids": deleted_shipment_ids,
        "lifecycle_events": lifecycle_events,
        "operations": operations,
        "total_data_blocks": total_data_blocks + replacement_data_blocks,
        "initial_data_blocks": total_data_blocks,
        "active_shipment_count": len(final_shipments),
        "read_operation_count": read_count,
        "write_operation_count": operation_count - read_count,
        "block_request_count": sum(operation["block_count"] for operation in operations),
    }


def run_experiment(
    workload: dict,
    allocation_algorithm: str,
    scheduling_algorithm: str,
) -> dict:
    """Run one allocation/scheduling pair against an isolated warehouse."""
    if allocation_algorithm not in ALLOCATION_ALGORITHMS:
        raise ValueError(f"Unknown allocation algorithm: {allocation_algorithm}")
    if scheduling_algorithm not in SCHEDULING_ALGORITHMS:
        raise ValueError(f"Unknown scheduling algorithm: {scheduling_algorithm}")

    inventory = create_inventory(BOX_COUNT, BLOCK_SIZE)
    allocations = {}
    for shipment in workload["shipments"]:
        blocks = generate_blocks(shipment, BLOCK_SIZE)
        result = allocate_blocks(blocks, inventory, allocation_algorithm)
        allocations[shipment["shipment_id"]] = result["allocation_metadata"]

    for shipment_id in workload["deleted_shipment_ids"]:
        deallocate_shipment(shipment_id, allocations[shipment_id], inventory)
        del allocations[shipment_id]

    for shipment in workload["replacement_shipments"]:
        blocks = generate_blocks(shipment, BLOCK_SIZE)
        try:
            result = allocate_blocks(blocks, inventory, allocation_algorithm)
        except ValueError as error:
            return {
                "allocation_algorithm": allocation_algorithm,
                "scheduling_algorithm": scheduling_algorithm,
                "allocation_success": False,
                "allocation_error": str(error),
                "storage_metrics": calculate_storage_metrics(inventory),
                "warehouse_map": [
                    {
                        "position": box["position"],
                        "occupied": box["occupied"],
                        "block_id": box["block_id"],
                        "shipment_id": box["shipment_id"],
                    }
                    for box in inventory["boxes"]
                ],
            }
        allocations[shipment["shipment_id"]] = result["allocation_metadata"]

    requests = []
    for operation in workload["operations"]:
        shipment_id = operation["shipment_id"]
        if shipment_id not in allocations:
            raise ValueError("Workload operation references a deleted shipment.")
        requests.extend(build_block_requests(
            shipment_id,
            allocations[shipment_id]["allocated_blocks"],
            operation["operation"],
            operation["arrival_time"],
            operation["operation_id"],
        ))

    schedule = schedule_requests(
        requests,
        current_position=INITIAL_WORKER_POSITION,
        algorithm=scheduling_algorithm,
        min_position=MIN_POSITION,
        max_position=MAX_POSITION,
        direction="up",
        timing=workload["config"]["timing"],
    )
    return {
        "allocation_algorithm": allocation_algorithm,
        "scheduling_algorithm": scheduling_algorithm,
        "allocation_success": True,
        "storage_metrics": calculate_storage_metrics(inventory),
        "schedule": schedule,
        "warehouse_map": [
            {
                "position": box["position"],
                "occupied": box["occupied"],
                "block_id": box["block_id"],
                "shipment_id": box["shipment_id"],
            }
            for box in inventory["boxes"]
        ],
        "shipment_positions": {
            shipment_id: [
                block["position"]
                for block in allocation["allocated_blocks"]
            ]
            for shipment_id, allocation in allocations.items()
        },
    }

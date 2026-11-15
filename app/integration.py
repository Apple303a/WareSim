"""Coordinate the storage engine with the Flask application."""

from shared.config import BLOCK_SIZE, BOX_COUNT
from shared.config import (
    INITIAL_WORKER_POSITION,
    MAX_POSITION,
    MIN_POSITION,
    SCHEDULING_ALGORITHMS,
)
from storage_engine.allocation import allocate_blocks, deallocate_shipment
from storage_engine.block_generator import generate_blocks
from storage_engine.inventory import calculate_storage_metrics, create_inventory
from storage_engine.shipment import create_shipment_record
from scheduling_engine.algorithms import DEFAULT_TIMING, schedule_requests
from scheduling_engine.request_queue import build_block_requests
from app.simulation import generate_workload, run_experiment


def create_simulation_state() -> dict:
    """Create in-memory state for one running application process."""
    return {
        "inventory": create_inventory(BOX_COUNT, BLOCK_SIZE),
        "shipments": {},
        "allocation_algorithm": None,
        "last_operation": None,
        "active_workload": None,
        "simulation_results": {},
    }


def set_allocation_algorithm(algorithm: str, state: dict) -> None:
    """Set the volume's allocation model while it has no allocated shipments."""
    supported_algorithms = {"contiguous", "linked", "indexed"}
    normalized_algorithm = algorithm.lower().strip()
    if normalized_algorithm not in supported_algorithms:
        raise ValueError(f"Unknown allocation algorithm: {algorithm}")
    if state["shipments"]:
        raise ValueError(
            "Allocation method cannot change while shipments are allocated. "
            "Delete all shipments first."
        )
    state["allocation_algorithm"] = normalized_algorithm


def create_shipment(data: dict, state: dict) -> dict:
    """Validate, allocate, and record a shipment."""
    algorithm = state["allocation_algorithm"]
    if algorithm is None:
        raise ValueError("Choose the warehouse allocation method before creating shipments.")

    shipment = create_shipment_record(data)
    shipment_id = shipment["shipment_id"]
    if shipment_id in state["shipments"]:
        raise ValueError(f"Shipment ID already exists: {shipment_id}")

    blocks = generate_blocks(shipment, BLOCK_SIZE)
    result = allocate_blocks(blocks, state["inventory"], algorithm)
    state["shipments"][shipment_id] = {
        "shipment": shipment,
        "allocation_metadata": result["allocation_metadata"],
    }
    return state["shipments"][shipment_id]


def delete_shipment(shipment_id: str, state: dict) -> None:
    """Release a shipment's boxes and remove its in-memory record."""
    shipment_data = state["shipments"].get(shipment_id)
    if shipment_data is None:
        raise KeyError(f"Shipment not found: {shipment_id}")

    deallocate_shipment(
        shipment_id,
        shipment_data["allocation_metadata"],
        state["inventory"],
    )
    del state["shipments"][shipment_id]


def get_dashboard_data(state: dict) -> dict:
    """Return storage inventory, metrics, and shipment records for display."""
    inventory = state["inventory"]
    shipments = []
    for shipment_data in state["shipments"].values():
        shipment = shipment_data["shipment"].copy()
        allocation = shipment_data["allocation_metadata"]
        shipment["allocation_algorithm"] = allocation["allocation_algorithm"]
        shipment["positions"] = [
            block["position"] for block in allocation["allocated_blocks"]
        ]
        shipments.append(shipment)

    return {
        "inventory": inventory,
        "metrics": calculate_storage_metrics(inventory),
        "shipments": shipments,
        "allocation_algorithm": state["allocation_algorithm"],
        "last_operation": state["last_operation"],
    }


def run_shipment_operation(data: dict, state: dict) -> dict:
    """Schedule one block-level operation for every block in a shipment."""
    shipment_id = data.get("shipment_id")
    if not isinstance(shipment_id, str) or not shipment_id.strip():
        raise ValueError("Shipment ID is required.")
    shipment_data = state["shipments"].get(shipment_id)
    if shipment_data is None:
        raise KeyError(f"Shipment not found: {shipment_id}")

    algorithm = data.get("algorithm")
    if not isinstance(algorithm, str):
        raise ValueError("Choose a scheduling algorithm.")
    normalized_algorithm = algorithm.lower().strip()
    if normalized_algorithm != "compare" and normalized_algorithm not in SCHEDULING_ALGORITHMS:
        raise ValueError(f"Unknown scheduling algorithm: {algorithm}")

    current_position = data.get("worker_position", INITIAL_WORKER_POSITION)
    direction = data.get("direction", "up")
    arrival_time = data.get("arrival_time", 0)
    requests = build_block_requests(
        shipment_id,
        shipment_data["allocation_metadata"]["allocated_blocks"],
        data.get("operation"),
        arrival_time,
    )
    algorithms = (
        SCHEDULING_ALGORITHMS
        if normalized_algorithm == "compare"
        else (normalized_algorithm,)
    )
    timing = data.get("timing", DEFAULT_TIMING)
    results = {
        name: schedule_requests(
            requests,
            current_position=current_position,
            algorithm=name,
            min_position=MIN_POSITION,
            max_position=MAX_POSITION,
            direction=direction,
            timing=timing,
        )
        for name in algorithms
    }

    operation_result = {
        "shipment_id": shipment_id,
        "operation": data["operation"].upper(),
        "algorithm": normalized_algorithm,
        "requests": requests,
        "results": results,
        "selected_result": next(iter(results.values())),
    }
    state["last_operation"] = operation_result
    return operation_result


def create_simulation_workload(data: dict, state: dict) -> dict:
    """Generate and store a workload to be reused across matrix cells."""
    workload = generate_workload(data)
    state["active_workload"] = workload
    state["simulation_results"] = {}
    return workload


def run_simulation_cell(data: dict, state: dict) -> dict:
    """Run one matrix cell against the currently selected workload."""
    workload = state["active_workload"]
    if workload is None:
        raise ValueError("Generate a workload before running a simulation cell.")
    if data.get("workload_id") != workload["workload_id"]:
        raise ValueError("The workload has changed. Generate or reload the current workload.")

    allocation_algorithm = data.get("allocation_algorithm")
    scheduling_algorithm = data.get("scheduling_algorithm")
    result = run_experiment(
        workload, allocation_algorithm, scheduling_algorithm
    )
    if state["active_workload"]["workload_id"] != workload["workload_id"]:
        raise ValueError("The workload changed while this cell was running; result was discarded.")
    key = f"{allocation_algorithm}:{scheduling_algorithm}"
    state["simulation_results"][key] = result
    return {"key": key, "result": result}

from flask import Blueprint, current_app, jsonify, render_template, request

from app.integration import (
    create_simulation_workload,
    create_shipment,
    delete_shipment,
    get_dashboard_data,
    run_simulation_cell,
    run_shipment_operation,
    set_allocation_algorithm,
)
from shared.config import ALLOCATION_ALGORITHMS, SCHEDULING_ALGORITHMS

main = Blueprint("main", __name__)


@main.get("/")
def dashboard():
    data = get_dashboard_data(current_app.extensions["waresim_state"])
    return render_template("dashboard.html", **data)


@main.get("/shipments")
def shipments():
    state = current_app.extensions["waresim_state"]
    return render_template(
        "shipments.html",
        allocation_algorithm=state["allocation_algorithm"],
        has_shipments=bool(state["shipments"]),
    )


@main.post("/api/storage/allocation")
def set_storage_allocation_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("algorithm"), str):
        return jsonify({"error": "Choose a valid allocation method."}), 400

    try:
        set_allocation_algorithm(
            data["algorithm"], current_app.extensions["waresim_state"]
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"allocation_algorithm": data["algorithm"].lower().strip()})


@main.post("/api/shipments")
def create_shipment_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send shipment details as a JSON object."}), 400

    try:
        shipment_data = create_shipment(
            data, current_app.extensions["waresim_state"]
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    shipment = shipment_data["shipment"]
    allocation = shipment_data["allocation_metadata"]
    return jsonify({
        "shipment": shipment,
        "allocation_metadata": allocation,
    }), 201


@main.delete("/api/shipments/<shipment_id>")
def delete_shipment_api(shipment_id):
    try:
        delete_shipment(shipment_id, current_app.extensions["waresim_state"])
    except KeyError as error:
        return jsonify({"error": str(error.args[0])}), 404

    return jsonify({"shipment_id": shipment_id, "status": "deleted"})


@main.get("/operations")
def operations():
    state = current_app.extensions["waresim_state"]
    return render_template(
        "operations.html",
        shipments=[
            item["shipment"] for item in state["shipments"].values()
        ],
        has_shipments=bool(state["shipments"]),
    )


@main.post("/api/operations")
def schedule_operation_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send operation details as a JSON object."}), 400

    try:
        result = run_shipment_operation(
            data, current_app.extensions["waresim_state"]
        )
    except KeyError as error:
        return jsonify({"error": str(error.args[0])}), 404
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(result)


@main.get("/simulations")
def simulations():
    state = current_app.extensions["waresim_state"]
    workload = state["active_workload"]
    next_seed = (
        (workload["config"]["seed"] + 1) % (2**31)
        if workload else 42
    )
    return render_template(
        "simulations.html",
        allocation_algorithms=ALLOCATION_ALGORITHMS,
        scheduling_algorithms=SCHEDULING_ALGORITHMS,
        workload=workload,
        next_seed=next_seed,
        workload_id=(
            workload["workload_id"] if workload else None
        ),
        simulation_results=state["simulation_results"],
    )


@main.post("/api/simulations/workload")
def create_simulation_workload_api():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Send workload settings as a JSON object."}), 400
    data = payload.copy()
    timing_keys = (
        "seek_time_per_position",
        "fixed_io_latency",
        "read_transfer_rate",
        "write_transfer_rate",
    )
    timing = {key: data.pop(key) for key in timing_keys if key in data}
    if timing:
        data["timing"] = timing

    try:
        workload = create_simulation_workload(
            data, current_app.extensions["waresim_state"]
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({
        "workload_id": workload["workload_id"],
        "config": workload["config"],
        "shipment_count": len(workload["shipments"]),
        "replacement_count": len(workload["replacement_shipments"]),
        "active_shipment_count": workload["active_shipment_count"],
        "deleted_shipment_count": len(workload["deleted_shipment_ids"]),
        "operation_count": len(workload["operations"]),
        "total_data_blocks": workload["total_data_blocks"],
        "read_operation_count": workload["read_operation_count"],
        "write_operation_count": workload["write_operation_count"],
        "block_request_count": workload["block_request_count"],
        "lifecycle_events": workload["lifecycle_events"],
        "operations": workload["operations"],
    }), 201


@main.post("/api/simulations/run")
def run_simulation_cell_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Choose a matrix cell to simulate."}), 400
    try:
        result = run_simulation_cell(
            data, current_app.extensions["waresim_state"]
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(result)

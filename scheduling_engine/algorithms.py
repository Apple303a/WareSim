"""Arrival-aware disk scheduling over linear warehouse positions."""

import math
from numbers import Real
from typing import Optional

from shared.config import SCHEDULING_ALGORITHMS
from scheduling_engine.metrics import calculate_metrics
from scheduling_engine.request_queue import validate_requests
from scheduling_engine.worker import Worker

DEFAULT_TIMING = {
    "seek_time_per_position": 1.0,
    "fixed_io_latency": 1.0,
    "read_transfer_rate": 100.0,
    "write_transfer_rate": 100.0,
}


def schedule_requests(
    requests: list[dict],
    current_position: int,
    algorithm: str,
    min_position: int = 0,
    max_position: int = 99,
    direction: str = "up",
    timing: Optional[dict] = None,
) -> dict:
    """Schedule block I/O requests and return movement, order, and metrics.

    Requests are non-preemptive. At each dispatch point only arrived requests
    are considered; a request selected for service completes after moving to
    its position and spending fixed latency plus transfer time on I/O. The
    timing dictionary configures seek cost per position, fixed I/O latency,
    and independent read/write transfer rates. New arrivals during a seek wait
    for the next dispatch point.
    """
    validate_requests(requests)
    if not isinstance(algorithm, str):
        raise ValueError("Scheduling algorithm must be a string.")
    normalized_algorithm = algorithm.lower().strip()
    if normalized_algorithm not in SCHEDULING_ALGORITHMS:
        raise ValueError(f"Unknown scheduling algorithm: {algorithm}")
    if direction not in ("up", "down"):
        raise ValueError("Direction must be 'up' or 'down'.")
    timing_values = dict(DEFAULT_TIMING)
    if timing is not None:
        if not isinstance(timing, dict):
            raise ValueError("Timing settings must be an object.")
        timing_values.update(timing)
    for name in DEFAULT_TIMING:
        value = timing_values[name]
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{name} must be a finite positive number.")
    seek_cost = timing_values["seek_time_per_position"]
    for label, position in (
        ("Minimum", min_position),
        ("Maximum", max_position),
        ("Worker", current_position),
    ):
        if not isinstance(position, int) or isinstance(position, bool):
            raise ValueError(f"{label} position must be an integer.")
    if min_position > max_position:
        raise ValueError("Minimum position cannot exceed maximum position.")
    if not min_position <= current_position <= max_position:
        raise ValueError("Worker position must be within the configured bounds.")
    for request in requests:
        if not min_position <= request["position"] <= max_position:
            raise ValueError(
                f"Request position {request['position']} is outside "
                f"{min_position}..{max_position}."
            )

    worker = Worker(current_position)
    movement_path = [current_position]
    request_order: list[str] = []
    timeline: list[dict] = []
    remaining = list(enumerate(requests))
    current_time = min(
        (request["arrival_time"] for request in requests), default=0.0
    )
    current_direction = direction

    def move_to(position: int) -> None:
        nonlocal current_time
        distance = worker.move_to(position)
        current_time += distance * seek_cost
        if position != movement_path[-1]:
            movement_path.append(position)

    while remaining:
        arrived = [
            (index, request)
            for index, request in remaining
            if request["arrival_time"] <= current_time
        ]
        if not arrived:
            current_time = min(request["arrival_time"] for _, request in remaining)
            arrived = [
                (index, request)
                for index, request in remaining
                if request["arrival_time"] <= current_time
            ]

        if normalized_algorithm == "fcfs":
            selected = min(
                arrived, key=lambda item: (item[1]["arrival_time"], item[0])
            )
        elif normalized_algorithm == "sstf":
            selected = min(
                arrived,
                key=lambda item: (
                    abs(item[1]["position"] - worker.position),
                    item[1]["arrival_time"],
                    item[0],
                ),
            )
        else:
            at_worker = [
                item for item in arrived if item[1]["position"] == worker.position
            ]
            if at_worker:
                selected = min(
                    at_worker, key=lambda item: (item[1]["arrival_time"], item[0])
                )
            else:
                ahead = [
                    item
                    for item in arrived
                    if (
                        item[1]["position"] > worker.position
                        if current_direction == "up"
                        else item[1]["position"] < worker.position
                    )
                ]
                if ahead:
                    selected = min(
                        ahead,
                        key=lambda item: (
                            item[1]["position"]
                            if current_direction == "up"
                            else -item[1]["position"],
                            item[1]["arrival_time"],
                            item[0],
                        ),
                    )
                else:
                    other_side = [
                        item
                        for item in arrived
                        if (
                            item[1]["position"] < worker.position
                            if current_direction == "up"
                            else item[1]["position"] > worker.position
                        )
                    ]
                    if not other_side:
                        # No currently arrived work is in this sweep's path.
                        # Wait for the next arrival without changing direction.
                        current_time = min(
                            request["arrival_time"] for _, request in remaining
                        )
                        continue

                    if normalized_algorithm in ("scan", "cscan"):
                        boundary = (
                            max_position if current_direction == "up" else min_position
                        )
                        move_to(boundary)
                        if normalized_algorithm == "scan":
                            current_direction = (
                                "down" if current_direction == "up" else "up"
                            )
                        else:
                            wrap_position = (
                                min_position if current_direction == "up" else max_position
                            )
                            move_to(wrap_position)
                    elif normalized_algorithm == "look":
                        current_direction = (
                            "down" if current_direction == "up" else "up"
                        )
                    else:  # C-LOOK: wrap to the furthest queued request on the other side.
                        wrap_target = (
                            min(item[1]["position"] for item in other_side)
                            if current_direction == "up"
                            else max(item[1]["position"] for item in other_side)
                        )
                        move_to(wrap_target)
                    continue

        index, request = selected
        seek_duration = abs(request["position"] - worker.position) * seek_cost
        move_to(request["position"])
        start_time = current_time
        transfer_rate_key = (
            "read_transfer_rate"
            if request["operation"].upper() == "READ"
            else "write_transfer_rate"
        )
        transfer_time = request["transfer_size"] / timing_values[transfer_rate_key]
        service_time = timing_values["fixed_io_latency"] + transfer_time
        device_service_time = seek_duration + service_time
        completion_time = start_time + service_time
        timeline.append({
            "request_id": request["request_id"],
            "operation": request["operation"].upper(),
            "position": request["position"],
            "transfer_size": request["transfer_size"],
            "seek_time": round(seek_duration, 4),
            "service_time": round(service_time, 4),
            "device_service_time": round(device_service_time, 4),
            "start_time": round(start_time, 4),
            "completion_time": round(completion_time, 4),
            "waiting_time": round(start_time - request["arrival_time"], 4),
            "response_time": round(start_time - request["arrival_time"], 4),
            "turnaround_time": round(completion_time - request["arrival_time"], 4),
        })
        current_time = completion_time
        request_order.append(request["request_id"])
        remaining = [(item_index, item) for item_index, item in remaining if item_index != index]

    metrics = calculate_metrics(
        requests, request_order, movement_path, timeline, current_time
    )
    return {
        "algorithm": normalized_algorithm,
        "initial_position": current_position,
        "final_position": worker.position,
        "direction": direction,
        "execution_order": request_order,
        "movement_path": movement_path,
        "total_movement": metrics["total_movement"],
        "execution_timeline": timeline,
        "timing_model": timing_values,
        "metrics": metrics,
    }

"""Scheduling metrics using simulated request start and completion times."""

from typing import Optional


def calculate_metrics(
    requests: list[dict],
    execution_order: list[str],
    movement_path: list[int],
    execution_timeline: Optional[list[dict]] = None,
    makespan: Optional[float] = None,
) -> dict:
    """Calculate queueing metrics and seek distance for a completed schedule.

    The scheduler supplies timeline entries because seek and service durations
    determine waiting and turnaround times.
    """
    total_movement = sum(
        abs(destination - source)
        for source, destination in zip(movement_path, movement_path[1:])
    )
    if not requests:
        return {
            "average_waiting_time": 0.0,
            "average_response_time": 0.0,
            "average_turnaround_time": 0.0,
            "throughput": 0.0,
            "average_read_latency": 0.0,
            "average_write_latency": 0.0,
            "average_read_service_time": 0.0,
            "average_write_service_time": 0.0,
            "average_seek_time": 0.0,
            "read_throughput_units_per_time": 0.0,
            "write_throughput_units_per_time": 0.0,
            "total_movement": total_movement,
        }
    if execution_timeline is None or len(execution_timeline) != len(requests):
        raise ValueError("A complete execution timeline is required for metrics.")

    count = len(execution_timeline)
    average_waiting_time = sum(
        item["waiting_time"] for item in execution_timeline
    ) / count
    average_response_time = sum(
        item["response_time"] for item in execution_timeline
    ) / count
    average_turnaround_time = sum(
        item["turnaround_time"] for item in execution_timeline
    ) / count
    first_arrival = min(request["arrival_time"] for request in requests)
    final_completion = max(item["completion_time"] for item in execution_timeline)
    elapsed_time = (
        makespan - first_arrival if makespan is not None
        else final_completion - first_arrival
    )
    throughput = count / elapsed_time if elapsed_time > 0 else 0.0
    read_items = [item for item in execution_timeline if item["operation"] == "READ"]
    write_items = [item for item in execution_timeline if item["operation"] == "WRITE"]

    def average(items: list[dict], field: str) -> float:
        if not items:
            return 0.0
        return round(sum(item[field] for item in items) / len(items), 2)

    read_size = sum(item["transfer_size"] for item in read_items)
    write_size = sum(item["transfer_size"] for item in write_items)

    return {
        "average_waiting_time": round(average_waiting_time, 2),
        "average_response_time": round(average_response_time, 2),
        "average_turnaround_time": round(average_turnaround_time, 2),
        "throughput": round(throughput, 4),
        "average_read_latency": average(read_items, "turnaround_time"),
        "average_write_latency": average(write_items, "turnaround_time"),
        "average_read_service_time": average(read_items, "service_time"),
        "average_write_service_time": average(write_items, "service_time"),
        "average_seek_time": round(
            sum(item["seek_time"] for item in execution_timeline) / count, 2
        ),
        "read_throughput_units_per_time": round(
            read_size / elapsed_time if elapsed_time > 0 else 0.0, 4
        ),
        "write_throughput_units_per_time": round(
            write_size / elapsed_time if elapsed_time > 0 else 0.0, 4
        ),
        "total_movement": total_movement,
    }

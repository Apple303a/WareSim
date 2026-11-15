import pytest

from scheduling_engine.algorithms import schedule_requests
from scheduling_engine.request_queue import build_block_requests, validate_requests


def _requests(positions, operation="READ"):
    return [{
        "request_id": f"R{index}",
        "shipment_id": "S",
        "block_id": f"B{index}",
        "operation": operation,
        "position": position,
        "transfer_size": 100,
        "arrival_time": 0,
        "priority": 1,
    } for index, position in enumerate(positions)]


@pytest.mark.parametrize(
    "algorithm,expected_order,expected_movement",
    [
        ("fcfs", ["R0", "R1", "R2", "R3", "R4", "R5", "R6"], 642),
        ("sstf", ["R2", "R4", "R5", "R0", "R3", "R1", "R6"], 208),
        ("scan", ["R0", "R3", "R1", "R6", "R2", "R4", "R5"], 332),
        ("cscan", ["R0", "R3", "R1", "R6", "R5", "R4", "R2"], 391),
        ("look", ["R0", "R3", "R1", "R6", "R2", "R4", "R5"], 314),
        ("clook", ["R0", "R3", "R1", "R6", "R5", "R4", "R2"], 341),
    ],
)
def test_classic_disk_scheduling_sequences(algorithm, expected_order, expected_movement):
    requests = _requests([82, 170, 43, 140, 24, 16, 190])
    result = schedule_requests(
        requests, current_position=50, algorithm=algorithm, max_position=199
    )
    assert result["execution_order"] == expected_order
    assert result["total_movement"] == expected_movement
    assert result["movement_path"][0] == 50
    assert result["metrics"]["throughput"] > 0


def test_arrival_times_and_configured_read_write_timing_affect_metrics():
    requests = _requests([1, 2])
    requests[1]["arrival_time"] = 10
    result = schedule_requests(
        requests,
        current_position=0,
        algorithm="fcfs",
        timing={
            "seek_time_per_position": 2,
            "fixed_io_latency": 1,
            "read_transfer_rate": 100,
            "write_transfer_rate": 50,
        },
    )
    assert result["execution_timeline"][0]["completion_time"] == 4
    assert result["execution_timeline"][1]["completion_time"] == 14
    assert result["metrics"]["average_read_latency"] == 4
    assert result["metrics"]["throughput"] == 0.1429

    write = schedule_requests(
        _requests([0], operation="WRITE"),
        current_position=0,
        algorithm="fcfs",
        timing={
            "seek_time_per_position": 1,
            "fixed_io_latency": 1,
            "read_transfer_rate": 100,
            "write_transfer_rate": 50,
        },
    )
    assert write["metrics"]["average_write_latency"] == 3
    assert write["metrics"]["write_throughput_units_per_time"] == 33.3333


def test_request_builder_and_validation_reject_invalid_or_duplicate_requests():
    blocks = [
        {"block_id": "B1", "position": 3, "used_size": 100},
        {"block_id": "B2", "position": 8, "used_size": 20},
    ]
    requests = build_block_requests("S", blocks, "read", 1.5, "OP-1")
    assert len(requests) == 2
    assert requests[0]["request_id"] == "S_OP-1_READ_1"
    assert requests[1]["transfer_size"] == 20
    with pytest.raises(ValueError, match="Duplicate request ID"):
        validate_requests(requests + [requests[0]])
    with pytest.raises(ValueError, match="non-negative"):
        schedule_requests(
            _requests([-1]), current_position=0, algorithm="fcfs"
        )


def test_empty_request_queue_has_zero_metrics():
    result = schedule_requests([], current_position=3, algorithm="sstf")
    assert result["movement_path"] == [3]
    assert result["total_movement"] == 0
    assert result["metrics"]["throughput"] == 0

"""Scheduling performance metrics."""

def calculate_metrics(requests: list[dict], execution_order: list[str],
                      movement_path: list[int]) -> dict:
    """Calculate waiting, response, turnaround, throughput and movement.

    Document the service-time and arrival-time assumptions used.
    """
    raise NotImplementedError

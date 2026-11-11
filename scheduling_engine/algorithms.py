"""Disk scheduling algorithms adapted to linear warehouse positions."""

def schedule_requests(requests: list[dict], current_position: int,
                      algorithm: str, min_position: int = 0,
                      max_position: int = 99, direction: str = "up") -> dict:
    """Return execution_order, movement_path, total_movement and metrics.

    Supported: fcfs, sstf, scan, cscan, look, clook.
    The returned movement_path includes current_position as its first item.
    """
    raise NotImplementedError

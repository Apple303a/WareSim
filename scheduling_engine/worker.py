"""Single-worker position tracking."""


class Worker:
    def __init__(self, position: int = 0):
        if not isinstance(position, int) or isinstance(position, bool):
            raise ValueError("Worker position must be an integer.")
        self.position = position

    def move_to(self, target_position: int) -> int:
        """Update position and return distance moved."""
        if not isinstance(target_position, int) or isinstance(target_position, bool):
            raise ValueError("Target position must be an integer.")
        distance = abs(target_position - self.position)
        self.position = target_position
        return distance

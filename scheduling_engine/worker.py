"""Single-worker movement and execution simulation."""

class Worker:
    def __init__(self, position: int = 0):
        self.position = position

    def move_to(self, target_position: int) -> int:
        """Update position and return distance moved."""
        raise NotImplementedError

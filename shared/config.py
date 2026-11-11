"""Simulation-wide defaults. Person 3 can expose these in the UI later."""

BLOCK_SIZE = 100
BOX_COUNT = 100
INITIAL_WORKER_POSITION = 0
MIN_POSITION = 0
MAX_POSITION = BOX_COUNT - 1

ALLOCATION_ALGORITHMS = ("contiguous", "linked", "indexed")
SCHEDULING_ALGORITHMS = ("fcfs", "sstf", "scan", "cscan", "look", "clook")
OPERATIONS = ("READ", "WRITE")

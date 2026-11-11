# Team Work Split

## Person 1 — Storage Management Engine
- Shipment validation and metadata
- Fixed-size block generation
- Contiguous, linked and indexed allocation
- Inventory and free-space tracking
- Deallocation and shipment size updates
- Utilization and internal fragmentation

Deliverable: standalone functions in `storage_engine/`.

Needs from Person 3: shipment form schema, block size and warehouse capacity.
Needs from Person 2: integer physical position convention.

## Person 2 — Warehouse Scheduling Engine
- Block-level request validation and queue
- FCFS, SSTF, SCAN, C-SCAN, LOOK and C-LOOK
- Single worker and current position
- Execution order and movement path
- Waiting, response, turnaround, throughput and movement metrics

Deliverable: standalone functions in `scheduling_engine/`.

Needs from Person 1: actual integer position for every allocated block.
Needs from Person 3: initial position, boundaries, direction and selected algorithm.

## Person 3 — UI, Integration and Analytics
- Flask app and routes
- Shipment and operation forms
- Allocation and scheduling selectors
- Warehouse map and worker movement visualization
- Comparison charts
- End-to-end integration and testing

Deliverable: working web app in `app/`.

Needs from Person 1: allocation, lookup, deallocation interfaces and inventory data.
Needs from Person 2: scheduler interface, execution order, movement path and metrics.

## Integration order
1. Freeze `shared/contracts.py`.
2. Each engine owner writes unit tests and sample input/output.
3. Person 3 integrates using those public interfaces.
4. Run all algorithms on identical workloads for fair comparison.

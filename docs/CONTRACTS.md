# Shared Contracts (source of truth)

See `shared/contracts.py` for TypedDict definitions.

## Fixed conventions
- Positions are zero-based integers.
- `box_id` identifies a box; `position` is the scheduler's physical address.
- One box contains exactly one block.
- One shipment operation expands to one request per block.
- Allocation metadata lists each data block's physical `position`. Linked
  allocation records also include `next_box`; indexed allocation metadata
  includes the index block's `index_box` and ordered `index_entries` (physical
  positions of its data blocks).
- A scheduling request includes `request_id`, `shipment_id`, `block_id`,
  `operation`, `position`, `transfer_size`, `arrival_time`, and `priority`.
- Scheduler output includes `execution_order` (request IDs), `movement_path`
  (integer positions including the initial position), `total_movement`, and metrics.

## Example block-level request

```json
{
  "request_id": "R501_B1",
  "shipment_id": "S101",
  "block_id": "S101_B1",
  "operation": "READ",
  "position": 4,
  "transfer_size": 100,
  "arrival_time": 0,
  "priority": 1
}
```

Do not change shared field names without agreement from all three members.

Scheduling requests also include `transfer_size`, in storage-size units.

## Scheduling model

- Requests are non-preemptive. At a dispatch point, only requests that have
  arrived are eligible; a selected request is serviced before choosing again.
- The `priority` field is reserved and is not used by these classic disk
  scheduling policies; ties are broken deterministically by arrival/input order.
- SCAN/C-SCAN travel to the configured endpoint; LOOK/C-LOOK turn at queued
  request positions. C-SCAN/C-LOOK wrap movement is included in total movement.
- The abstract timing model charges seek time per position moved, fixed I/O
  latency per block request, and transfer size divided by the operation-specific
  transfer rate. Values are simulation units, not hardware measurements.
- The Simulation Lab's default demo uses 1 time unit per position moved, 1
  fixed time unit per block request, and a transfer rate of 100 size units per
  time unit for both READ and WRITE. One shipment-level operation expands into
  one request per allocated data block.
- The Simulation Lab lists lifecycle events in execution order: initial
  shipment creation, selected deletions, retained shipments, then replacement
  creations. Each allocation/scheduling pair replays that workload from an
  empty warehouse.
- Waiting/response time is arrival-to-service-start; turnaround and READ/WRITE
  latency are arrival-to-completion. Throughput is completed requests (or
  transferred size units) per elapsed simulation time.
- External fragmentation is free boxes outside the largest contiguous free
  extent. This is a textbook contiguous-allocation measure; linked/indexed
  allocation can generally use noncontiguous free boxes.

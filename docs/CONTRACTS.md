# Shared Contracts (source of truth)

See `shared/contracts.py` for TypedDict definitions.

## Fixed conventions
- Positions are zero-based integers.
- `box_id` identifies a box; `position` is the scheduler's physical address.
- One box contains exactly one block.
- One shipment operation expands to one request per block.
- A scheduling request includes `request_id`, `shipment_id`, `block_id`,
  `operation`, `position`, `arrival_time`, and `priority`.
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
  "arrival_time": 0,
  "priority": 1
}
```

Do not change shared field names without agreement from all three members.

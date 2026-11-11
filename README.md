# WareSim

Warehouse Management Simulator demonstrating Operating Systems concepts:
- File allocation: contiguous, linked and indexed allocation
- Free-space management
- Disk I/O scheduling: FCFS, SSTF, SCAN, C-SCAN, LOOK and C-LOOK
- Worker movement and performance comparison

## Team ownership

| Area | Owner | Folder |
|---|---|---|
| Storage management engine | Person 1 | `storage_engine/` |
| Warehouse scheduling engine | Person 2 | `scheduling_engine/` |
| Flask UI, integration and analytics | Person 3 | `app/` |

## Setup (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000`.

## Shared rules

1. Use Python dictionaries/lists with the field names defined in `shared/contracts.py`.
2. Box positions are zero-based integers: `0, 1, 2, ...`.
3. One box stores exactly one block; one block belongs to exactly one shipment.
4. Each shipment-level operation expands into one request per required block.
5. The scheduler receives physical integer positions, never shipment IDs alone.
6. Keep the two engines independent of Flask. The UI calls their public functions.
7. Compare algorithms on identical workloads, arrival times and initial worker positions.

## Current status

This repository is a shared scaffold. Engine functions are placeholders until their owners implement them.
See `docs/TEAM_WORK_SPLIT.md` and `docs/CONTRACTS.md` before coding.

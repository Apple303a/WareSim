from app import create_app


def test_shipment_creation_updates_dashboard():
    app = create_app()
    client = app.test_client()

    configured = client.post("/api/storage/allocation", json={"algorithm": "contiguous"})
    assert configured.status_code == 200
    response = client.post("/api/shipments", json={
        "shipment_id": "S-1",
        "name": "Sensors",
        "owner": "Warehouse",
        "size": 250,
    })

    assert response.status_code == 201
    result = response.get_json()
    assert [block["position"] for block in result["allocation_metadata"]["allocated_blocks"]] == [0, 1, 2]

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert b"3.0%" in dashboard.data
    assert b"S-1" in dashboard.data
    assert b"S-1_B3" in dashboard.data


def test_rejected_shipment_does_not_change_dashboard():
    app = create_app()
    client = app.test_client()
    client.post("/api/storage/allocation", json={"algorithm": "contiguous"})
    client.post("/api/shipments", json={
        "shipment_id": "S-1",
        "name": "Sensors",
        "owner": "Warehouse",
        "size": 100,
    })

    duplicate = client.post("/api/shipments", json={
        "shipment_id": "S-1",
        "name": "Duplicate",
        "owner": "Warehouse",
        "size": 100,
    })
    too_large = client.post("/api/shipments", json={
        "shipment_id": "S-2",
        "name": "Too large",
        "owner": "Warehouse",
        "size": 10100,
    })

    assert duplicate.status_code == 400
    assert too_large.status_code == 400
    dashboard = client.get("/")
    assert b"1.0%" in dashboard.data
    assert b"Duplicate" not in dashboard.data
    assert b"S-2" not in dashboard.data


def test_linked_allocation_uses_noncontiguous_free_boxes_and_can_be_deleted():
    app = create_app()
    client = app.test_client()
    configured = client.post("/api/storage/allocation", json={"algorithm": "linked"})
    assert configured.status_code == 200

    for shipment_id, size in (("A", 100), ("B", 100)):
        response = client.post("/api/shipments", json={
            "shipment_id": shipment_id,
            "name": shipment_id,
            "owner": "Warehouse",
            "size": size,
        })
        assert response.status_code == 201

    deleted = client.delete("/api/shipments/A")
    assert deleted.status_code == 200

    response = client.post("/api/shipments", json={
        "shipment_id": "C",
        "name": "C",
        "owner": "Warehouse",
        "size": 200,
    })
    assert response.status_code == 201
    blocks = response.get_json()["allocation_metadata"]["allocated_blocks"]
    assert [block["position"] for block in blocks] == [0, 2]
    assert [block["next_box"] for block in blocks] == [2, None]

    dashboard = client.get("/")
    assert b"A_B1" not in dashboard.data
    assert b"C_B1" in dashboard.data
    assert b"3 / 100" in dashboard.data

    missing = client.delete("/api/shipments/A")
    assert missing.status_code == 404


def test_allocation_model_is_volume_wide_and_locked_while_in_use():
    app = create_app()
    client = app.test_client()

    missing_selection = client.post("/api/shipments", json={
        "shipment_id": "S-1",
        "name": "Sensors",
        "owner": "Warehouse",
        "size": 100,
    })
    assert missing_selection.status_code == 400

    configured = client.post("/api/storage/allocation", json={"algorithm": "linked"})
    assert configured.status_code == 200

    created = client.post("/api/shipments", json={
        "shipment_id": "S-1",
        "name": "Sensors",
        "owner": "Warehouse",
        "size": 100,
    })
    assert created.status_code == 201
    assert created.get_json()["allocation_metadata"]["allocation_algorithm"] == "linked"

    changed = client.post("/api/storage/allocation", json={"algorithm": "indexed"})
    assert changed.status_code == 400
    assert b"linked" in client.get("/").data


def test_manual_operation_api_schedules_block_requests():
    app = create_app()
    client = app.test_client()
    client.post("/api/storage/allocation", json={"algorithm": "linked"})
    client.post("/api/shipments", json={
        "shipment_id": "MANUAL",
        "name": "Manual test",
        "owner": "Warehouse",
        "size": 250,
    })

    response = client.post("/api/operations", json={
        "shipment_id": "MANUAL",
        "operation": "READ",
        "algorithm": "compare",
        "worker_position": 0,
        "direction": "up",
        "arrival_time": 0,
    })

    assert response.status_code == 200
    data = response.get_json()
    assert len(data["requests"]) == 3
    assert set(data["results"]) == {
        "fcfs", "sstf", "scan", "cscan", "look", "clook"
    }
    assert data["results"]["fcfs"]["metrics"]["average_read_latency"] > 0


def test_simulation_matrix_reuses_one_seeded_workload():
    app = create_app()
    client = app.test_client()
    config = {
        "shipment_count": 4,
        "replacement_count": 2,
        "minimum_size": 100,
        "maximum_size": 100,
        "operation_count": 5,
        "read_percent": 60,
        "delete_percent": 25,
        "seed": 7,
        "arrival_span": 10,
    }

    workload_response = client.post("/api/simulations/workload", json=config)
    assert workload_response.status_code == 201
    workload_data = workload_response.get_json()
    workload_id = workload_data["workload_id"]
    assert workload_data["operation_count"] == 5
    assert workload_data["config"]["timing"] == {
        "seek_time_per_position": 1.0,
        "fixed_io_latency": 1.0,
        "read_transfer_rate": 100.0,
        "write_transfer_rate": 100.0,
    }
    lifecycle = workload_data["lifecycle_events"]
    assert [event["sequence"] for event in lifecycle] == list(
        range(1, len(lifecycle) + 1)
    )
    assert [event["action"] for event in lifecycle] == [
        "CREATE", "CREATE", "CREATE", "CREATE",
        "DELETE",
        "RETAIN", "RETAIN", "RETAIN",
        "CREATE", "CREATE",
    ]
    assert sum(operation["block_count"] for operation in workload_data["operations"]) == (
        workload_data["block_request_count"]
    )

    first = client.post("/api/simulations/run", json={
        "allocation_algorithm": "linked",
        "scheduling_algorithm": "fcfs",
        "workload_id": workload_id,
    })
    second = client.post("/api/simulations/run", json={
        "allocation_algorithm": "linked",
        "scheduling_algorithm": "sstf",
        "workload_id": workload_id,
    })
    assert first.status_code == second.status_code == 200
    first_result = first.get_json()["result"]
    second_result = second.get_json()["result"]
    assert first_result["warehouse_map"] == second_result["warehouse_map"]
    assert first_result["storage_metrics"] == second_result["storage_metrics"]

    page = client.get("/simulations")
    assert page.status_code == 200
    assert b"Run all 18 for this workload" in page.data
    assert b"Shipment lifecycle" in page.data
    assert b"Declare winner by" in page.data
    assert b"seek-time-per-position" not in page.data
    assert b"linked" in page.data


def test_external_fragmentation_measures_free_boxes_outside_largest_run():
    from storage_engine.inventory import calculate_storage_metrics, create_inventory

    inventory = create_inventory(6, 100)
    for position in (1, 3):
        inventory["boxes"][position]["occupied"] = True
    metrics = calculate_storage_metrics(inventory)
    assert metrics["free_boxes"] == 4
    assert metrics["largest_free_extent"] == 2
    assert metrics["external_fragmentation_units"] == 2
    assert metrics["external_fragmentation_pct"] == 50.0


def test_fragmented_contiguous_allocation_can_fail_while_other_models_reuse_holes():
    from app.simulation import run_experiment
    from scheduling_engine.algorithms import DEFAULT_TIMING

    initial_shipments = [
        {
            "shipment_id": f"INITIAL-{index:02d}",
            "name": "Initial",
            "owner": "Test",
            "size": 300,
        }
        for index in range(25)
    ]
    replacements = [
        {
            "shipment_id": f"REPLACEMENT-{index:02d}",
            "name": "Replacement",
            "owner": "Test",
            "size": 400,
        }
        for index in range(7)
    ]
    workload = {
        "shipments": initial_shipments,
        "deleted_shipment_ids": [
            shipment["shipment_id"] for shipment in initial_shipments[::2][:10]
        ],
        "replacement_shipments": replacements,
        "operations": [{
            "operation_id": "OP-1",
            "shipment_id": replacements[0]["shipment_id"],
            "operation": "READ",
            "arrival_time": 0,
        }],
        "config": {"timing": DEFAULT_TIMING},
    }

    contiguous = run_experiment(workload, "contiguous", "fcfs")
    linked = run_experiment(workload, "linked", "fcfs")
    indexed = run_experiment(workload, "indexed", "fcfs")

    assert contiguous["allocation_success"] is False
    assert "External fragmentation" in contiguous["allocation_error"]
    assert linked["allocation_success"] is True
    assert indexed["allocation_success"] is True

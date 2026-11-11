"""Acceptance test suite for Person 1 Storage Engine."""
from storage_engine.shipment import create_shipment_record
from storage_engine.block_generator import generate_blocks
from storage_engine.inventory import create_inventory, get_shipment_positions
from storage_engine.allocation import allocate_blocks, deallocate_shipment, resize_shipment
from storage_engine.metrics import calculate_utilization, calculate_internal_fragmentation

def run_tests():
    print("========================================")
    print("Testing Storage Engine (Person 1)")
    print("========================================")

    # 1. Validation & Record Creation
    shipment_raw = {"shipment_id": "SHP_100", "size": 250, "name": "Sensors", "owner": "Logistics"}
    shipment = create_shipment_record(shipment_raw)
    assert shipment["shipment_id"] == "SHP_100"
    print("[PASS] Shipment Record Validation")

    # 2. Block Generation
    bg = generate_blocks(shipment, block_size=100)
    assert len(bg["blocks"]) == 3
    assert bg["blocks"][0]["used_size"] == 100
    assert bg["blocks"][1]["used_size"] == 100
    assert bg["blocks"][2]["used_size"] == 50
    print("[PASS] Block Generator (Contract A: 3 blocks, last used_size=50)")

    # 3. Contiguous Allocation
    inv = create_inventory(box_count=10, box_capacity=100)
    alloc_contig = allocate_blocks(bg, inv, algorithm="contiguous")
    pos_contig = get_shipment_positions("SHP_100", alloc_contig["allocation_metadata"])
    assert pos_contig == [0, 1, 2]
    print(f"[PASS] Contiguous Allocation (Positions: {pos_contig})")

    # 4. Metrics
    util = calculate_utilization(inv)
    frag = calculate_internal_fragmentation(inv)
    assert util == 30.0
    assert frag == 50
    print(f"[PASS] Metrics: Utilization = {util}%, Internal Fragmentation = {frag} units")

    # 5. Deallocation
    deallocate_shipment("SHP_100", alloc_contig["allocation_metadata"], inv)
    assert calculate_utilization(inv) == 0.0
    print("[PASS] Deallocation: All boxes freed")

    # 6. Linked Allocation
    alloc_linked = allocate_blocks(bg, inv, algorithm="linked")
    assert alloc_linked["allocation_metadata"]["allocated_blocks"][0]["next_box"] == 1
    print("[PASS] Linked Allocation (Linked pointers intact)")

    # 7. Indexed Allocation
    inv2 = create_inventory(box_count=10, box_capacity=100)
    alloc_indexed = allocate_blocks(bg, inv2, algorithm="indexed")
    assert "index_box" in alloc_indexed["allocation_metadata"]
    print(f"[PASS] Indexed Allocation (Index box: {alloc_indexed['allocation_metadata']['index_box']})")

    # 8. Resize Shipment
    resized = resize_shipment("SHP_100", new_size=150, block_size=100,
                              allocation_metadata=alloc_indexed["allocation_metadata"],
                              inventory=inv2)
    assert len(resized["allocation_metadata"]["allocated_blocks"]) == 2
    print("[PASS] Resize Shipment: Shrunk to 2 blocks")

    print("========================================")
    print("ALL ACCEPTANCE TESTS PASSED!")
    print("========================================")

if __name__ == "__main__":
    run_tests()
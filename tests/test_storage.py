"""Acceptance test suite for Person 1 Storage Engine."""
import copy

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
    assert alloc_indexed["allocation_metadata"]["index_entries"] == [1, 2, 3]
    print(f"[PASS] Indexed Allocation (Index box: {alloc_indexed['allocation_metadata']['index_box']})")

    # 8. Resize Shipment
    resized = resize_shipment("SHP_100", new_size=150, block_size=100,
                              allocation_metadata=alloc_indexed["allocation_metadata"],
                              inventory=inv2)
    assert len(resized["allocation_metadata"]["allocated_blocks"]) == 2
    assert resized["allocation_metadata"]["index_entries"] == [1, 2]
    print("[PASS] Resize Shipment: Shrunk to 2 blocks")

    # Same block count must still update the final block's used size.
    same_count_inventory = create_inventory(box_count=5, box_capacity=100)
    same_count_allocation = allocate_blocks(
        generate_blocks({"shipment_id": "SAME", "size": 250}, 100),
        same_count_inventory,
        algorithm="linked"
    )["allocation_metadata"]
    resize_shipment("SAME", 210, 100, same_count_allocation, same_count_inventory)
    assert same_count_inventory["boxes"][2]["used_size"] == 10
    print("[PASS] Resize within the same block count updates used size")

    # Shrinking a linked allocation must terminate its retained chain.
    linked_inventory = create_inventory(box_count=5, box_capacity=100)
    linked_allocation = allocate_blocks(
        generate_blocks({"shipment_id": "LINKED", "size": 250}, 100),
        linked_inventory,
        algorithm="linked"
    )["allocation_metadata"]
    resize_shipment("LINKED", 150, 100, linked_allocation, linked_inventory)
    assert linked_allocation["allocated_blocks"][-1]["next_box"] is None
    assert linked_inventory["boxes"][1]["used_size"] == 50
    print("[PASS] Linked shrink updates chain and final block size")

    # Failed growth must leave both inventory and metadata untouched.
    small_inventory = create_inventory(box_count=3, box_capacity=100)
    small_allocation = allocate_blocks(
        generate_blocks({"shipment_id": "ATOMIC", "size": 200}, 100),
        small_inventory,
        algorithm="linked"
    )["allocation_metadata"]
    inventory_before = copy.deepcopy(small_inventory)
    allocation_before = copy.deepcopy(small_allocation)
    try:
        resize_shipment("ATOMIC", 400, 100, small_allocation, small_inventory)
    except ValueError:
        pass
    else:
        raise AssertionError("Growth beyond warehouse capacity should fail")
    assert small_inventory == inventory_before
    assert small_allocation == allocation_before
    print("[PASS] Failed growth preserves the existing shipment")

    # Successful growth reallocates the shipment and reports all new blocks.
    grow_inventory = create_inventory(box_count=5, box_capacity=100)
    grow_allocation = allocate_blocks(
        generate_blocks({"shipment_id": "GROW", "size": 100}, 100),
        grow_inventory,
        algorithm="linked"
    )["allocation_metadata"]
    grown = resize_shipment("GROW", 250, 100, grow_allocation, grow_inventory)
    assert len(grown["allocation_metadata"]["allocated_blocks"]) == 3
    assert sum(box["occupied"] for box in grow_inventory["boxes"]) == 3
    assert grow_inventory["boxes"][2]["used_size"] == 50
    print("[PASS] Successful growth reallocates blocks and updates used size")

    print("========================================")
    print("ALL ACCEPTANCE TESTS PASSED!")
    print("========================================")

if __name__ == "__main__":
    run_tests()
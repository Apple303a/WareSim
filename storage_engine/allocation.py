"""Contiguous, linked and indexed allocation."""
import copy
import math

def allocate_blocks(blocks: dict, inventory: dict, algorithm: str) -> dict:
    """
    Allocate blocks and return allocation metadata plus updated inventory.
    Every allocated block must expose block_id, box_id and integer position.
    """
    shipment_id = blocks["shipment_id"]
    block_list = blocks["blocks"]
    num_blocks = len(block_list)
    box_list = inventory["boxes"]

    free_indices = [i for i, b in enumerate(box_list) if not b["occupied"]]

    algo = algorithm.lower().strip()

    if algo == "contiguous":
        start_index = -1
        consecutive = 0

        for i, b in enumerate(box_list):
            if not b["occupied"]:
                if consecutive == 0:
                    start_index = i
                consecutive += 1
                if consecutive == num_blocks:
                    break
            else:
                consecutive = 0
                start_index = -1

        if consecutive < num_blocks:
            raise ValueError("Contiguous Allocation Failed: External fragmentation.")

        allocated_blocks = []
        for offset, blk in enumerate(block_list):
            pos = start_index + offset
            box_list[pos]["occupied"] = True
            box_list[pos]["block_id"] = blk["block_id"]
            box_list[pos]["shipment_id"] = shipment_id
            box_list[pos]["used_size"] = blk["used_size"]
            allocated_blocks.append({
                "block_id": blk["block_id"],
                "box_id": box_list[pos]["box_id"],
                "position": pos
            })

        metadata = {
            "shipment_id": shipment_id,
            "allocation_algorithm": "contiguous",
            "allocated_blocks": allocated_blocks
        }
        return {"allocation_metadata": metadata, "inventory": inventory}

    elif algo == "linked":
        if len(free_indices) < num_blocks:
            raise ValueError("Linked Allocation Failed: Warehouse Full.")

        chosen_indices = free_indices[:num_blocks]
        allocated_blocks = []

        for i, blk in enumerate(block_list):
            pos = chosen_indices[i]
            next_box = chosen_indices[i + 1] if i + 1 < num_blocks else None
            box_list[pos]["occupied"] = True
            box_list[pos]["block_id"] = blk["block_id"]
            box_list[pos]["shipment_id"] = shipment_id
            box_list[pos]["used_size"] = blk["used_size"]
            allocated_blocks.append({
                "block_id": blk["block_id"],
                "box_id": box_list[pos]["box_id"],
                "position": pos,
                "next_box": next_box
            })

        metadata = {
            "shipment_id": shipment_id,
            "allocation_algorithm": "linked",
            "allocated_blocks": allocated_blocks
        }
        return {"allocation_metadata": metadata, "inventory": inventory}

    elif algo == "indexed":
        if len(free_indices) < num_blocks + 1:
            raise ValueError("Indexed Allocation Failed: Need boxes for blocks + 1 index box.")

        index_pos = free_indices[0]
        data_indices = free_indices[1:num_blocks + 1]

        box_list[index_pos]["occupied"] = True
        box_list[index_pos]["block_id"] = f"{shipment_id}_INDEX"
        box_list[index_pos]["shipment_id"] = shipment_id
        box_list[index_pos]["used_size"] = inventory.get("box_capacity", 100)

        allocated_blocks = []
        for i, blk in enumerate(block_list):
            pos = data_indices[i]
            box_list[pos]["occupied"] = True
            box_list[pos]["block_id"] = blk["block_id"]
            box_list[pos]["shipment_id"] = shipment_id
            box_list[pos]["used_size"] = blk["used_size"]
            allocated_blocks.append({
                "block_id": blk["block_id"],
                "box_id": box_list[pos]["box_id"],
                "position": pos
            })

        metadata = {
            "shipment_id": shipment_id,
            "allocation_algorithm": "indexed",
            "index_box": index_pos,
            "index_entries": data_indices.copy(),
            "allocated_blocks": allocated_blocks
        }
        return {"allocation_metadata": metadata, "inventory": inventory}

    else:
        raise ValueError(f"Unknown allocation algorithm: {algorithm}")


def deallocate_shipment(shipment_id: str, allocation_metadata: dict, inventory: dict) -> dict:
    """Free every box belonging to the shipment and return updated state."""
    box_list = inventory["boxes"]
    for b in box_list:
        if b.get("shipment_id") == shipment_id:
            b["occupied"] = False
            b["block_id"] = None
            b["shipment_id"] = None
            b["used_size"] = 0

    return {
        "status": "deallocated",
        "shipment_id": shipment_id,
        "inventory": inventory
    }


def resize_shipment(shipment_id: str, new_size: int, block_size: int, allocation_metadata: dict, inventory: dict) -> dict:
    """Resize a shipment, leaving its original allocation intact if growth fails."""
    if not isinstance(new_size, int) or isinstance(new_size, bool) or new_size <= 0:
        raise ValueError("Shipment size must be a positive integer.")
    if not isinstance(block_size, int) or isinstance(block_size, bool) or block_size <= 0:
        raise ValueError("Block size must be a positive integer.")

    allocated_blocks = allocation_metadata.get("allocated_blocks", [])
    current_block_count = len(allocated_blocks)
    new_block_count = math.ceil(new_size / block_size)

    def update_used_sizes(blocks: list[dict]) -> None:
        remaining_size = new_size
        for block in blocks:
            used_size = min(remaining_size, block_size)
            block["used_size"] = used_size
            inventory["boxes"][block["position"]]["used_size"] = used_size
            remaining_size -= used_size

    if new_block_count == current_block_count:
        update_used_sizes(allocated_blocks)
        return {"allocation_metadata": allocation_metadata, "inventory": inventory}

    algorithm = allocation_metadata.get("allocation_algorithm", "linked")

    # If shrinking
    if new_block_count < current_block_count:
        blocks_to_keep = allocated_blocks[:new_block_count]
        blocks_to_free = allocated_blocks[new_block_count:]

        box_list = inventory["boxes"]
        for blk in blocks_to_free:
            pos = blk["position"]
            box_list[pos]["occupied"] = False
            box_list[pos]["block_id"] = None
            box_list[pos]["shipment_id"] = None
            box_list[pos]["used_size"] = 0

        allocation_metadata["allocated_blocks"] = blocks_to_keep
        if algorithm == "linked":
            for index, block in enumerate(blocks_to_keep):
                block["next_box"] = (
                    blocks_to_keep[index + 1]["position"]
                    if index + 1 < len(blocks_to_keep)
                    else None
                )
        elif algorithm == "indexed":
            allocation_metadata["index_entries"] = [
                block["position"] for block in blocks_to_keep
            ]
        update_used_sizes(blocks_to_keep)
        return {"allocation_metadata": allocation_metadata, "inventory": inventory}

    # Allocate against a working copy so a failed growth cannot lose the old shipment.
    working_inventory = copy.deepcopy(inventory)
    deallocate_shipment(shipment_id, allocation_metadata, working_inventory)
    from .block_generator import generate_blocks
    new_blocks = generate_blocks({"shipment_id": shipment_id, "size": new_size}, block_size)
    result = allocate_blocks(new_blocks, working_inventory, algorithm)

    for existing_box, resized_box in zip(inventory["boxes"], working_inventory["boxes"]):
        existing_box.clear()
        existing_box.update(resized_box)

    return {"allocation_metadata": result["allocation_metadata"], "inventory": inventory}
"""Shipment validation and metadata."""

def validate_shipment(shipment: dict) -> None:
    """Validate required fields and raise ValueError for invalid input."""
    if not isinstance(shipment, dict):
        raise ValueError("Shipment must be a dictionary.")

    required_fields = ["shipment_id", "size"]
    for field in required_fields:
        if field not in shipment:
            raise ValueError(f"Missing required shipment field: '{field}'")

    if not isinstance(shipment["size"], int) or shipment["size"] <= 0:
        raise ValueError("Shipment size must be a positive integer.")

    if not str(shipment["shipment_id"]).strip():
        raise ValueError("Shipment ID cannot be empty.")


def create_shipment_record(shipment: dict) -> dict:
    """Return a normalized shipment record."""
    validate_shipment(shipment)
    return {
        "shipment_id": str(shipment["shipment_id"]),
        "name": shipment.get("name", "Unnamed Shipment"),
        "owner": shipment.get("owner", "Unknown"),
        "size": shipment["size"]
    }
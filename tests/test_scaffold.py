def test_shared_contracts_import():
    from shared import contracts
    assert hasattr(contracts, "ShipmentInput")

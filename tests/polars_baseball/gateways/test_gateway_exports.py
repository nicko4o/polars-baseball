from polars_baseball.gateways import BRefGateway, CompiledDatasetGateway, MlbStatsGateway, SavantGateway


def test_gateway_package_exports_current_gateways() -> None:
    assert BRefGateway.__name__ == "BRefGateway"
    assert CompiledDatasetGateway.__name__ == "CompiledDatasetGateway"
    assert MlbStatsGateway.__name__ == "MlbStatsGateway"
    assert SavantGateway.__name__ == "SavantGateway"

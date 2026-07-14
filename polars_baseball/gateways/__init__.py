"""External data boundary gateways."""

from polars_baseball.gateways.bref import BRefGateway
from polars_baseball.gateways.compiled import CompiledDatasetGateway
from polars_baseball.gateways.mlb import MlbStatsGateway
from polars_baseball.gateways.savant import SavantGateway

__all__ = [
    "BRefGateway",
    "CompiledDatasetGateway",
    "MlbStatsGateway",
    "SavantGateway",
]

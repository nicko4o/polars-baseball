"""Baseball Savant and Statcast data access."""

from __future__ import annotations

from polars_baseball._savant import (
    SavantGamefeedMixin,
    SavantParkFactorsMixin,
    SavantProfilesMixin,
    SavantStatcastMixin,
)
from polars_baseball.client import BaseballClient
from polars_baseball.gateways.savant import SavantGateway
from polars_baseball.gateways.statcast_dataset import StatcastDatasetGateway


class SavantClient(
    SavantStatcastMixin,
    SavantGamefeedMixin,
    SavantParkFactorsMixin,
    SavantProfilesMixin,
):
    """Namespaced Baseball Savant and Statcast client."""

    def __init__(self, client: BaseballClient) -> None:
        self._client = client
        self._gateway = SavantGateway(client)
        self._dataset_gateway = StatcastDatasetGateway(client)


__all__ = ["SavantClient"]

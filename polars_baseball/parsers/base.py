from abc import ABC, abstractmethod

import polars as pl


class BaseParser(ABC):
    """Abstract parser for converting raw HTTP response content into normalized DataFrames.

    Subclasses implement parse() for a specific provider's HTML, CSV, or JSON format.
    """

    @abstractmethod
    def parse(self, raw: str) -> pl.DataFrame:
        """Parse raw content into a normalized DataFrame."""
        pass

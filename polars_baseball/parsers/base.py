from abc import ABC, abstractmethod

import polars as pl


class BaseParser(ABC):
    @abstractmethod
    def parse(self, raw: str) -> pl.DataFrame:
        """Parse raw content into a normalized DataFrame."""
        pass

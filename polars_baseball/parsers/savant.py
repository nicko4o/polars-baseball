import io

import polars as pl

from polars_baseball._config import DEFAULT_CSV_INFER_SCHEMA_LENGTH
from polars_baseball.parsers.base import BaseParser
from polars_baseball.parsers.savant_schema import SAVANT_SCHEMA_OVERRIDES


class SavantCSVParser(BaseParser):
    def parse(self, raw: str) -> pl.DataFrame:
        return self._to_dataframe(raw)

    @staticmethod
    def _to_dataframe(csv_data: str) -> pl.DataFrame:
        if not csv_data.strip():
            return pl.DataFrame()

        df = pl.read_csv(
            io.BytesIO(csv_data.encode("utf-8")),
            infer_schema_length=DEFAULT_CSV_INFER_SCHEMA_LENGTH,
            null_values=[""],
        )

        df = df.rename({col: col.strip() for col in df.columns})

        string_cols = [col for col, dtype in df.schema.items() if dtype == pl.String]
        if string_cols:
            df = df.with_columns(pl.col(c).str.strip_chars().alias(c) for c in string_cols)

        active_casts = {k: v for k, v in SAVANT_SCHEMA_OVERRIDES.items() if k in df.columns}
        if active_casts:
            df = df.with_columns(pl.col(k).cast(v, strict=False).alias(k) for k, v in active_casts.items())

        return df

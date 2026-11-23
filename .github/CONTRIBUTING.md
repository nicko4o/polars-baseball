# Contributing to polars-baseball

Pull requests are welcome. Please keep changes focused, typed, and covered by offline unit tests.

## Local Setup

```bash
git clone https://github.com/nicko4o/polars-baseball.git
cd polars-baseball
uv sync --all-extras
```

## Verification

Run before opening a PR:

```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy polars_baseball/
uv run pytest tests/polars_baseball -m "not live"
```

## Guidelines

- **Polars & async-first**: Data-fetching APIs are `async def` on `BaseballClient` subclients and return `polars.DataFrame` (or `pl.LazyFrame` / `list[pl.DataFrame]` where documented). Never introduce pandas.
- **Explicit schemas**: DataFrame outputs must be backed by Polars schema contracts in `polars_baseball/_schemas/` or parsers.
- **Offline tests**: Unit tests use mocked fixtures in `tests/polars_baseball/data/` and must not hit the network. Mark live integration tests with `@pytest.mark.live`.
- **Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `ci:`).

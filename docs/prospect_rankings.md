> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Prospect Rankings

`prospect_rankings(list_type: str = "top100", year: int | None = None, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves the MLB Pipeline prospect rankings for a given list type and year.

---

## Arguments

- `list_type`: The type of prospect list to retrieve. Defaults to `"top100"`. Supported options:
  - `"top100"`: Top 100 prospects overall.
  - `"draft"`: Top draft prospects.
  - `"international"`: Top international prospects.
  - Position codes: `"c"`, `"1b"`, `"2b"`, `"3b"`, `"ss"`, `"of"`, `"rhp"`, `"lhp"`.
  - Team names: Fetch top 30 rankings for a specific team (e.g. `"yankees"`, `"redsox"`, `"dbacks"`).
- `year`: Optional historical year. If not specified, the current rankings are returned.
- `context`: Optional dependency injection context.

---

## Examples

### 1. Fetch Top 100 Prospects

```python
import asyncio
from polars_baseball import prospect_rankings

async def main() -> None:
    df = await prospect_rankings("top100")
    print(df.head(5))

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Fetch Team Specific Top 30 Rankings

```python
import asyncio
from polars_baseball import prospect_rankings

async def main() -> None:
    df = await prospect_rankings("yankees")
    print(df.head(5))

if __name__ == "__main__":
    asyncio.run(main())
```

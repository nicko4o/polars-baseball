> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Top Prospects

`top_prospects(team_name: str | None = None, player_type: str | None = None) -> pl.DataFrame`

Retrieves MLB top-prospect data for one team or leaguewide.

## Arguments

- `team_name`: Team name without whitespace, such as `bluejays` or `padres`. If omitted, leaguewide prospects are returned.
- `player_type`: `pitchers` or `batters`. If omitted, both groups are returned.

## Example

```python
import asyncio
from polars_baseball import top_prospects

async def main() -> None:
    blue_jays_pitchers = await top_prospects("bluejays", "pitchers")
    leaguewide = await top_prospects()
    leaguewide_batters = await top_prospects(None, "batters")
    padres = await top_prospects("padres")
    print(blue_jays_pitchers.head())
    print(leaguewide.head())
    print(leaguewide_batters.head())
    print(padres.head())

if __name__ == "__main__":
    asyncio.run(main())
```

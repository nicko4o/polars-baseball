> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Baseball Reference

Functions for retrieving daily WAR (Wins Above Replacement) and historical statistics from Baseball Reference.

---

## Rate Limiting and Cloudflare

> [!WARNING]
> Baseball Reference enforces a strict rate limit of **10 requests per minute**. Going above this limit will result in an HTTP 429 response.
> Furthermore, some endpoints are protected by Cloudflare Turnstile security. During live verification, Baseball Reference may return an HTTP 403 Forbidden error. Consequently, guaranteed non-empty executable code examples are omitted.

---

## Batting WAR

Retrieves Baseball Reference daily batting WAR data from the `war_daily_bat` database table.

### Functions

- `bwar_bat(return_all: bool = False) -> pl.DataFrame`

### Arguments

- `return_all`: When `True`, returns all available columns from the `war_daily_bat` table. When `False`, returns the standard subset of columns commonly used in analytics workflows.

---

## Pitching WAR

Retrieves Baseball Reference daily pitching WAR data from the `war_daily_pitch` database table.

### Functions

- `bwar_pitch(return_all: bool = False) -> pl.DataFrame`

### Arguments

- `return_all`: When `True`, returns all available columns from the `war_daily_pitch` table. When `False`, returns the standard subset of columns commonly used in analytics workflows.

---

## Output DataFrame Schema

### BRef Daily WAR Schema (`bwar_bat`, `bwar_pitch`)

| Column Name | Polars Type | Description |
| --- | --- | --- |
| `name_common` | `pl.String` | Player common name. |
| `player_ID` | `pl.String` | Baseball Reference player ID (`key_bbref`). |
| `year_ID` | `pl.Int64` | Season year. |
| `team_ID` | `pl.String` | Team abbreviation. |
| `stint_ID` | `pl.Int64` | Stint identifier for players traded mid-season. |
| `WAR` | `pl.Float64` | Wins Above Replacement. |
| `salary` | `pl.Int64` | Player salary in USD (where available). |
| `PA` / `IPruns` | `pl.Float64` | Plate appearances (batting) or Innings Pitched runs (pitching). |

---

## Example

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    # Fetch standard daily batting WAR (may raise HTTP 403 in live environments)
    try:
        batting_war = await pb.bref.bwar_bat(all_columns=False)
        print("Batting WAR:", batting_war.head())
    except Exception as e:
        print("Could not retrieve Batting WAR:", e)

    # Fetch standard daily pitching WAR
    try:
        pitching_war = await pb.bref.bwar_pitch(all_columns=False)
        print("Pitching WAR:", pitching_war.head())
    except Exception as e:
        print("Could not retrieve Pitching WAR:", e)

if __name__ == "__main__":
    asyncio.run(main())
```

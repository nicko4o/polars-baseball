# Jupyter Notebook Usage

Jupyter and IPython already run an event loop. Call async APIs with top-level `await` in notebook cells.

Do not wrap notebook cells with `asyncio.run()`. That is for standalone Python scripts and will fail inside a running notebook event loop.

## Statcast Cell

```python
import polars_baseball as pb

df = await pb.statcast(start_date="2026-06-01", end_date="2026-06-01")
df.head()
```

## Player Query Cell

```python
import polars_baseball as pb

pitches = await pb.statcast_pitcher(
    start_date="2026-06-01",
    end_date="2026-06-01",
    player_id=506433,
)
pitches.select(["game_date", "pitch_type", "release_speed"]).head()
```

## Polars Display

Notebook cells can return a `polars.DataFrame` as the last expression. Use `.head()`, `.select()`, and `.filter()` to keep rendered output small.

```python
import polars as pl
import polars_baseball as pb

pitches = await pb.statcast_pitcher(
    start_date="2026-06-01",
    end_date="2026-06-01",
    player_id=506433,
)
summary = (
    pitches
    .group_by("pitch_type")
    .agg(pl.col("release_speed").mean().alias("mean_speed"))
    .sort("mean_speed", descending=True)
)
summary
```

## Cache Behavior

Notebook sessions do not write cache files unless you call `configure_cache()` first. Long-running notebooks should call `cleanup()` before kernel shutdown when they are done with package-managed HTTP resources.

```python
import polars_baseball as pb

await pb.cleanup()
```

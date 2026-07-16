# Jupyter Notebook 使用方式

Jupyter 與 IPython 已經有執行中的 event loop。Notebook cell 裡呼叫非同步 API 時，直接使用 top-level `await`。

不要在 Notebook cell 裡包 `asyncio.run()`。那是給獨立 Python script 用的，在已經有 event loop 的 Notebook 內會失敗。

## Statcast Cell

```python
import polars_baseball as pb

df = await pb.statcast(start_date="2024-05-06", end_date="2024-05-06")
df.head()
```

## Player Query Cell

```python
import polars_baseball as pb

pitches = await pb.statcast_pitcher(
    start_date="2024-05-06",
    end_date="2024-05-06",
    player_id=506433,
)
pitches.select(["game_date", "pitch_type", "release_speed"]).head()
```

## Polars 顯示

Notebook cell 可以把 `polars.DataFrame` 放在最後一行直接顯示。使用 `.head()`、`.select()`、`.filter()` 控制輸出大小。

```python
import polars as pl
import polars_baseball as pb

pitches = await pb.statcast_pitcher(
    start_date="2024-05-06",
    end_date="2024-05-06",
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

## 快取行為

Notebook session 和 script 使用同一套 package cache：預設為 `~/.polars_baseball/cache`。長時間執行的 Notebook 如果用到套件管理的 HTTP resource，結束 kernel 前應呼叫 `cleanup()`。

```python
import polars_baseball as pb

await pb.cleanup()
```

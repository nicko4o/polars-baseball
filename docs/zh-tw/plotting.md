> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# 資料視覺化

`polars-baseball` 不提供繪圖 API。它只回傳原生 `polars.DataFrame`，讓使用者自行選擇視覺化工具。

`plot` extra 只會安裝本文範例使用的第三方函式庫。你也可以在自己的專案中直接安裝 hvPlot、Altair、Plotly、Matplotlib、seaborn 或任何其他視覺化函式庫。`polars-baseball` 只負責資料擷取契約。

## 安裝

若要執行本文範例，可安裝選用範例依賴：

```bash
pip install "polars-baseball[plot]"
```

## Smoke Test

先用本地 DataFrame 驗證繪圖依賴是否正確安裝：

```python
import hvplot.polars  # noqa: F401
import polars as pl

df = pl.DataFrame({"x": [1, 2], "y": [3, 4]})
chart = df.plot.scatter(x="x", y="y")
print(chart)
```

## 使用 hvPlot 建立互動式 spray chart

```python
import asyncio

import hvplot.polars  # noqa: F401
import polars_baseball as bp


async def main() -> None:
    df = await bp.statcast(start_dt="2024-05-06", end_dt="2024-05-06")
    batted_df = df.filter(df["hc_x"].is_not_null() & df["hc_y"].is_not_null())
    chart = batted_df.plot.scatter(
        x="hc_x",
        y="hc_y",
        by="events",
        invert_y=True,
    )
    print(chart)


if __name__ == "__main__":
    asyncio.run(main())
```

## 使用 Altair 建立互動式 strike zone

```python
import asyncio

import altair as alt
import polars_baseball as bp


async def main() -> None:
    df = await bp.statcast_pitcher(
        start_dt="2024-05-06",
        end_dt="2024-05-06",
        player_id=506433,
    )
    pitch_df = df.filter(df["plate_x"].is_not_null() & df["plate_z"].is_not_null())

    scatter_chart = alt.Chart(pitch_df).mark_circle(size=80).encode(
        x="plate_x",
        y="plate_z",
        color="pitch_type",
        tooltip=["player_name", "pitch_type", "release_speed", "description"],
    )
    strike_zone = alt.Chart(
        {"values": [{"x": -0.83, "x2": 0.83, "y": 1.5, "y2": 3.5}]}
    ).mark_rect(
        fillOpacity=0,
        stroke="black",
    ).encode(
        x="x:Q",
        x2="x2:Q",
        y="y:Q",
        y2="y2:Q",
    )
    final_chart = (scatter_chart + strike_zone).interactive()
    final_chart.show()


if __name__ == "__main__":
    asyncio.run(main())
```

## 為什麼繪圖維持在專案外

- **核心依賴較小**：預設安裝維持專注於棒球資料擷取。
- **使用者自主管理 rendering stack**：使用者自行選擇符合專案需求的圖表函式庫、notebook renderer、瀏覽器輸出、靜態匯出流程與樣式系統。
- **相容性邊界清楚**：第三方繪圖 API 不屬於 `polars-baseball` 的 public API contract。
- **Polars-first workflow**：範例從回傳的 `polars.DataFrame` 開始；支援 Polars 或 Arrow 的視覺化函式庫可以直接使用這些資料。

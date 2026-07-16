> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Data Visualization

`polars-baseball` does not provide a plotting API. It returns native `polars.DataFrame` objects so users can choose their own visualization stack.

The `plot` extra only installs third-party libraries used by the examples below. You may also install hvPlot, Altair, Plotly, Matplotlib, seaborn, or any other visualization library directly in your own project. `polars-baseball` only owns the data retrieval contract.

## Installation

To run the examples in this guide, install the optional example dependencies:

```bash
pip install "polars-baseball[plot]"
```

## Smoke Test

Use a local DataFrame first to verify that the plotting dependencies are installed correctly:

```python
import hvplot.polars  # noqa: F401
import polars as pl

df = pl.DataFrame({"x": [1, 2], "y": [3, 4]})
chart = df.plot.scatter(x="x", y="y")
print(chart)
```

## Interactive Spray Chart with hvPlot

```python
import asyncio

import hvplot.polars  # noqa: F401
import polars_baseball as bp


async def main() -> None:
    df = await bp.statcast(start_date="2024-05-06", end_date="2024-05-06")
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

## Interactive Strike Zone with Altair

```python
import asyncio

import altair as alt
import polars_baseball as bp


async def main() -> None:
    df = await bp.statcast_pitcher(
        start_date="2024-05-06",
        end_date="2024-05-06",
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

## Why Keep Plotting External

- **Small core dependency graph**: The default install stays focused on baseball data retrieval.
- **User-owned rendering stack**: Users choose the charting library, notebook renderer, browser output, static export path, and style system that fits their project.
- **Clear compatibility boundary**: Third-party plotting APIs are not part of the `polars-baseball` public API contract.
- **Polars-first workflow**: Examples start from the returned `polars.DataFrame`; visualization libraries that support Polars or Arrow can consume the data directly.

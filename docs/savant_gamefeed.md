> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Savant Gamefeed API

Retrieves Baseball Savant per-game JSON datasets and returns `polars.DataFrame` objects.
New code can call the shorter `polars_baseball.savant` namespace, such as `pb.savant.gamefeed_pitch_data(...)`.
The existing `savant_gamefeed_*` root functions remain supported.

## Exit Velocity (`savant_gamefeed_exit_velocity`)

`savant_gamefeed_exit_velocity(game_pk: int | str, context: BaseballContext | None = None) -> pl.DataFrame`

Fetches exit velocity rows for a single MLB game.

## Exit Velocity Batch (`savant_gamefeed_exit_velocity_many`)

`savant_gamefeed_exit_velocity_many(game_pks: Sequence[int | str], context: BaseballContext | None = None, parallel: bool = True) -> pl.DataFrame`

Fetches exit velocity rows for multiple games and concatenates them.

## Pitch Data (`savant_gamefeed_pitch_data`)

`savant_gamefeed_pitch_data(game_pk: int | str, context: BaseballContext | None = None) -> pl.DataFrame`

Fetches pitch-level gamefeed rows for a single MLB game.

## Pitch Data Batch (`savant_gamefeed_pitch_data_many`)

`savant_gamefeed_pitch_data_many(game_pks: Sequence[int | str], context: BaseballContext | None = None, parallel: bool = True) -> pl.DataFrame`

Fetches pitch-level gamefeed rows for multiple games and concatenates them.

## Example

```python
import asyncio

import polars_baseball as pb

async def main() -> None:
    exit_velocity = await pb.savant.gamefeed_exit_velocity(745585)
    pitch_data = await pb.savant.gamefeed_pitch_data_many([745585, "746639"])
    print(exit_velocity.head())
    print(pitch_data.head())

if __name__ == "__main__":
    asyncio.run(main())
```

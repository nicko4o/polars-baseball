> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Savant Gamefeed API

擷取 Baseball Savant 單場比賽 JSON 資料集，並回傳 `polars.DataFrame`。
新程式碼可使用較短的 `polars_baseball.savant` namespace，例如 `pb.savant.gamefeed_pitch_data(...)`。

## Exit Velocity (`savant.gamefeed_exit_velocity`)

`savant.gamefeed_exit_velocity(game_pk: int | str, context: BaseballContext | None = None) -> pl.DataFrame`

擷取單場 MLB 比賽的 exit velocity rows。

## Exit Velocity Batch (`savant.gamefeed_exit_velocity_many`)

`savant.gamefeed_exit_velocity_many(game_pks: Sequence[int | str], context: BaseballContext | None = None, parallel: bool = True) -> pl.DataFrame`

擷取多場比賽的 exit velocity rows 並合併。

## Pitch Data (`savant.gamefeed_pitch_data`)

`savant.gamefeed_pitch_data(game_pk: int | str, context: BaseballContext | None = None) -> pl.DataFrame`

擷取單場 MLB 比賽的 pitch-level gamefeed rows。

## Pitch Data Batch (`savant.gamefeed_pitch_data_many`)

`savant.gamefeed_pitch_data_many(game_pks: Sequence[int | str], context: BaseballContext | None = None, parallel: bool = True) -> pl.DataFrame`

擷取多場比賽的 pitch-level gamefeed rows 並合併。

## 範例

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

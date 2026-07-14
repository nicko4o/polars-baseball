import enum


class ArsenalType(str, enum.Enum):
    """Pitch arsenal stat type for statcast_pitcher_pitch_arsenal.

    Use enum values at the public API boundary::

        statcast_pitcher_pitch_arsenal(2024, arsenal_type=ArsenalType.AVG_SPEED)
    """

    AVG_SPEED = "avg_speed"
    N_ = "n_"
    AVG_SPIN = "avg_spin"

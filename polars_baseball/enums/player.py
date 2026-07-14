import enum


class KeyType(str, enum.Enum):
    """Player ID key type for reverse lookups.

    Use enum values at the public API boundary::

        playerid_reverse_lookup([545361], key_type=KeyType.MLBAM)
    """

    MLBAM = "mlbam"
    RETRO = "retro"
    BBREF = "bbref"
    FANGRAPHS = "fangraphs"

from enum import IntEnum, unique


@unique
class PlayMode(IntEnum):
    OSU = 0
    TAIKO = 1
    CATCH = 2
    MANIA = 3

    def __iter__(self):
        return iter((self.OSU, self.TAIKO, self.CATCH, self.MANIA))

    def to_db(self, s: str) -> str:
        match self.name:
            case "OSU":
                return s + "_std"
            case "TAIKO":
                return s + "_taiko"
            case "CATCH":
                return s + "_catch"
            case "MANIA":
                return s + "_mania"
            case _:
                return "undefined"


@unique
class Gamemode(IntEnum):
    VANILLA = 0
    RELAX = 1

    def __iter__(self):
        return iter((self.VANILLA, self.RELAX))

    @property
    def table(self):
        return (
            "stats"
            if self == self.VANILLA
            else "stats_rx" if self == self.RELAX else "error"
        )

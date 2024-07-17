from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Timestamp:
    value: int
    MAX_VALUE: int = 2**40 - 1

    def __post_init__(self):
        if not (0 <= self.value <= self.MAX_VALUE):
            raise ValueError("Timestamp value out of bounds")

    def __lt__(self, other):
        return self.value < other.value

    def __gt__(self, other):
        return self.value > other.value

    def __ge__(self, other):
        return self.value >= other.value

    def __le__(self, other):
        return self.value <= other.value

    def __eq__(self, other):
        return self.value == other.value

    def __ne__(self, other):
        return self.value != other.value

    def is_zero(self):
        return self.value == 0

    def is_not_zero(self):
        return self.value != 0

    def to_seconds(self):
        return self.value

    @classmethod
    def from_uint256(cls, value):
        if value > cls.MAX_VALUE:
            raise ValueError("Timestamp overflow")
        return cls(value)

    @classmethod
    def now(cls):
        return cls(int(datetime.now().timestamp()))


class Timestamps:
    ZERO = Timestamp(0)
    MIN = ZERO
    MAX = Timestamp(Timestamp.MAX_VALUE)

    @staticmethod
    def now():
        return Timestamp.now()

    @staticmethod
    def from_uint256(value):
        return Timestamp.from_uint256(value)

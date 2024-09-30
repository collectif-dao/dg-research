from dataclasses import dataclass


class ETHValueOverflow(Exception):
    pass


class ETHValueUnderflow(Exception):
    pass


MAX_VALUE: int = 2**128 - 1


@dataclass(frozen=True)
class ETHValue:
    value: int

    def __post_init__(self):
        if not (0 <= self.value <= MAX_VALUE):
            raise ValueError("ETHValue value out of bounds")

    @staticmethod
    def from_uint256(value: int) -> "ETHValue":
        if value > 2**128 - 1:
            raise ETHValueOverflow
        return ETHValue(value)

    def __add__(self, other: "ETHValue") -> "ETHValue":
        return ETHValue.from_uint256(self.value + other.value)

    def __sub__(self, other: "ETHValue") -> "ETHValue":
        if self.value < other.value:
            raise ETHValueUnderflow
        return ETHValue.from_uint256(self.value - other.value)

    def __lt__(self, other: "ETHValue") -> bool:
        return self.value < other.value

    def __gt__(self, other: "ETHValue") -> bool:
        return self.value > other.value

    def __eq__(self, other: "ETHValue") -> bool:
        return self.value == other.value

    def __ne__(self, other: "ETHValue") -> bool:
        return self.value != other.value

    def to_uint256(self) -> int:
        return self.value


@dataclass(frozen=True)
class ETHValues:
    value: int

    ZERO: int = 0
    MAX_VALUE: int = MAX_VALUE

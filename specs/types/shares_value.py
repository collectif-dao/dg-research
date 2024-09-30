from dataclasses import dataclass

from .eth_value import ETHValue


class SharesValueOverflow(Exception):
    pass


class SharesValueUnderflow(Exception):
    pass


@dataclass(frozen=True)
class SharesValue:
    value: int
    ZERO: int = 0
    MAX_VALUE: int = 2**128 - 1

    def __post_init__(self):
        if not (0 <= self.value <= self.MAX_VALUE):
            raise ValueError("SharesValue value out of bounds")

    @staticmethod
    def from_uint256(value: int) -> "SharesValue":
        if value > 2**128 - 1:
            raise SharesValueOverflow
        return SharesValue(value)

    @staticmethod
    def calc_eth_value(total_pooled: ETHValue, share: "SharesValue", total: "SharesValue") -> ETHValue:
        return ETHValue.from_uint256((total_pooled.value * share.value) // total.value)

    def __add__(self, other: "SharesValue") -> "SharesValue":
        return SharesValue.from_uint256(self.value + other.value)

    def __sub__(self, other: "SharesValue") -> "SharesValue":
        if self.value < other.value:
            raise SharesValueUnderflow
        return SharesValue.from_uint256(self.value - other.value)

    def __lt__(self, other: "SharesValue") -> bool:
        return self.value < other.value

    def __gt__(self, other: "SharesValue") -> bool:
        return self.value > other.value

    def __eq__(self, other: "SharesValue") -> bool:
        return self.value == other.value

    def __ne__(self, other: "SharesValue") -> bool:
        return self.value != other.value

    def to_uint256(self) -> int:
        return self.value

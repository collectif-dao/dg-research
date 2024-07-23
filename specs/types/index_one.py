from dataclasses import dataclass


class IndexOneBasedOverflow(Exception):
    pass


class IndexOneBasedUnderflow(Exception):
    pass


max_value: int = 2**32 - 1


@dataclass(frozen=True)
class IndexOneBased:
    value: int

    @staticmethod
    def fromValue(value: int) -> "IndexOneBased":
        if value > 2**32 - 1:
            raise IndexOneBasedOverflow

        return IndexOneBased(value)

    def __ne__(self: "IndexOneBased", other: "IndexOneBased") -> bool:
        return self.value != other.value

    def get_value(self: "IndexOneBased") -> int:
        if self.value == 0:
            raise IndexOneBasedUnderflow
        return self.value - 1

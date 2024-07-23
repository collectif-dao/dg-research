from dataclasses import dataclass, field

BATCH_SIZE_LENGTH = 16
BATCH_SIZE_MASK = (1 << BATCH_SIZE_LENGTH) - 1

MAX_BATCH_SIZE = BATCH_SIZE_MASK
MAX_BATCH_VALUE = (1 << (256 - BATCH_SIZE_LENGTH)) - 1


class BatchValueOverflow(Exception):
    pass


class InvalidBatchSize(Exception):
    pass


class IndexOutOfBounds(Exception):
    pass


@dataclass
class SequentialBatch:
    value: int = field(default_factory=lambda: 0)

    @staticmethod
    def capacity() -> int:
        return MAX_BATCH_SIZE

    def size(self) -> int:
        return self.value & BATCH_SIZE_MASK

    def first(self) -> int:
        return self.value >> BATCH_SIZE_LENGTH

    def last(self) -> int:
        return self.first() + self.size() - 1

    def value_at(self, index: int) -> int:
        if index >= self.size():
            raise IndexOutOfBounds(index)

        return self.first() + index


class SequentialBatches:
    @staticmethod
    def create(seed: int, count: int) -> SequentialBatch:
        if seed > MAX_BATCH_VALUE:
            raise BatchValueOverflow()

        if count == 0 or count > MAX_BATCH_SIZE:
            raise InvalidBatchSize(count)

        return SequentialBatch(seed << BATCH_SIZE_LENGTH | count)

    @staticmethod
    def can_merge(b1: SequentialBatch, b2: SequentialBatch) -> bool:
        return b1.last() == b2.first() and SequentialBatch.capacity() - b1.size() > 0

    @staticmethod
    def merge(b1: SequentialBatch, b2: SequentialBatch) -> SequentialBatch:
        return SequentialBatches.create(b1.first(), b1.size() + b2.size())

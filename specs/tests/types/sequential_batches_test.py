import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.types.sequential_batches import (
    MAX_BATCH_SIZE,
    MAX_BATCH_VALUE,
    BatchValueOverflow,
    IndexOutOfBounds,
    InvalidBatchSize,
    SequentialBatch,
    SequentialBatches,
)


def test_sequential_batch_capacity():
    assert SequentialBatch.capacity() == MAX_BATCH_SIZE


@given(st.integers(min_value=0, max_value=MAX_BATCH_VALUE), st.integers(min_value=1, max_value=MAX_BATCH_SIZE))
def test_sequential_batch_create(seed, count):
    batch = SequentialBatches.create(seed, count)

    assert batch.size() == count
    assert batch.first() == seed
    assert batch.last() == seed + count - 1


@given(st.integers(min_value=0, max_value=MAX_BATCH_VALUE), st.integers(min_value=1, max_value=MAX_BATCH_SIZE))
def test_sequential_batch_value_at(seed, count):
    batch = SequentialBatches.create(seed, count)

    for i in range(count):
        assert batch.value_at(i) == seed + i


def test_sequential_batch_value_at_out_of_bounds():
    batch = SequentialBatches.create(0, 10)

    with pytest.raises(IndexOutOfBounds):
        batch.value_at(10)


def test_sequential_batches_create_invalid_seed():
    with pytest.raises(BatchValueOverflow):
        SequentialBatches.create(MAX_BATCH_VALUE + 1, 1)


def test_sequential_batches_create_invalid_size():
    with pytest.raises(InvalidBatchSize):
        SequentialBatches.create(0, 0)

    with pytest.raises(InvalidBatchSize):
        SequentialBatches.create(0, MAX_BATCH_SIZE + 1)


@given(
    st.integers(min_value=0, max_value=MAX_BATCH_VALUE // 2), st.integers(min_value=1, max_value=MAX_BATCH_SIZE // 2)
)
def test_sequential_batches_merge(seed, count):
    batch1 = SequentialBatches.create(seed, count)
    batch2 = SequentialBatches.create(seed + count, count)

    if seed + count != seed:
        assert not SequentialBatches.can_merge(batch1, batch2)
    else:
        merged_batch = SequentialBatches.merge(batch1, batch2)

        assert merged_batch.size() == batch1.size() + batch2.size()
        assert merged_batch.first() == batch1.first()
        assert merged_batch.last() == batch2.last()


def test_sequential_batches_can_merge():
    batch1 = SequentialBatches.create(10, 1)
    batch2 = SequentialBatches.create(10, 20)

    assert batch1.size() + batch2.size() <= SequentialBatch.capacity()
    assert SequentialBatches.can_merge(batch1, batch2)


def test_sequential_batches_cannot_merge():
    batch1 = SequentialBatches.create(0, 10)
    batch2 = SequentialBatches.create(11, 10)
    assert not SequentialBatches.can_merge(batch1, batch2)

import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.types.index_one import IndexOneBased, IndexOneBasedOverflow, IndexOneBasedUnderflow, max_value

base_strategy = st.integers(min_value=1, max_value=max_value)


@given(value=st.integers(min_value=0, max_value=max_value))
def test_fromValue(value):
    index = IndexOneBased.fromValue(value)
    assert index.value == value


@given(value=st.integers(min_value=max_value + 1))
def test_fromValue_overflow(value):
    with pytest.raises(IndexOneBasedOverflow):
        IndexOneBased.fromValue(value)


@given(base_strategy, base_strategy)
def test_ne(value1, value2):
    index1 = IndexOneBased(value1)
    index2 = IndexOneBased(value2)
    assert (index1 != index2) == (value1 != value2)


@given(base_strategy)
def test_value(value):
    index = IndexOneBased(value)

    assert index.get_value() == value - 1


def test_value_underflow():
    index = IndexOneBased(0)
    with pytest.raises(IndexOneBasedUnderflow):
        index.get_value()

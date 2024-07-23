import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.types.eth_value import ETHValue, ETHValueOverflow, ETHValues, ETHValueUnderflow

eth_value_strategy = st.integers(min_value=0, max_value=2**128 - 1)


@given(eth_value_strategy)
def test_from_uint256(value):
    eth_value = ETHValue.from_uint256(value)
    assert eth_value.value == value


@given(st.integers(min_value=2**128))
def test_from_uint256_overflow(value):
    with pytest.raises(ETHValueOverflow):
        ETHValue.from_uint256(value)


@given(v1=eth_value_strategy, v2=eth_value_strategy)
def test_add(v1, v2):
    eth_value1 = ETHValue.from_uint256(v1)
    eth_value2 = ETHValue.from_uint256(v2)

    if (v1 + v2) > 2**128 - 1:
        pytest.raises(ETHValueOverflow)
    else:
        result = eth_value1 + eth_value2
        assert result.value == v1 + v2


@given(v1=eth_value_strategy, v2=eth_value_strategy)
def test_sub(v1, v2):
    eth_value1 = ETHValue.from_uint256(v1)
    eth_value2 = ETHValue.from_uint256(v2)

    if v1 >= v2:
        result = eth_value1 - eth_value2
        assert result.value == v1 - v2
    else:
        with pytest.raises(ETHValueUnderflow):
            eth_value1 - eth_value2


@given(v1=eth_value_strategy, v2=eth_value_strategy)
def test_lt(v1, v2):
    eth_value1 = ETHValue.from_uint256(v1)
    eth_value2 = ETHValue.from_uint256(v2)
    assert (eth_value1 < eth_value2) == (v1 < v2)


@given(v1=eth_value_strategy, v2=eth_value_strategy)
def test_gt(v1, v2):
    eth_value1 = ETHValue.from_uint256(v1)
    eth_value2 = ETHValue.from_uint256(v2)
    assert (eth_value1 > eth_value2) == (v1 > v2)


@given(v1=eth_value_strategy, v2=eth_value_strategy)
def test_eq(v1, v2):
    eth_value1 = ETHValue.from_uint256(v1)
    eth_value2 = ETHValue.from_uint256(v2)
    assert (eth_value1 == eth_value2) == (v1 == v2)


@given(v1=eth_value_strategy, v2=eth_value_strategy)
def test_ne(v1, v2):
    eth_value1 = ETHValue.from_uint256(v1)
    eth_value2 = ETHValue.from_uint256(v2)
    assert (eth_value1 != eth_value2) == (v1 != v2)


@given(eth_value_strategy)
def test_to_uint256(value):
    eth_value = ETHValue.from_uint256(value)
    assert eth_value.to_uint256() == value


def test_constants():
    assert ETHValues.ZERO == 0
    assert ETHValues.MAX_VALUE == 2**128 - 1

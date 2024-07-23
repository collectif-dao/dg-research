import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.types.eth_value import ETHValue, ETHValueOverflow
from specs.types.shares_value import SharesValue, SharesValueOverflow, SharesValueUnderflow

shares_value_strategy = st.integers(min_value=0, max_value=2**128 - 1)


@given(shares_value_strategy)
def test_from_uint256(value):
    shares_value = SharesValue.from_uint256(value)
    assert shares_value.value == value


@given(st.integers(min_value=2**128))
def test_from_uint256_overflow(value):
    with pytest.raises(SharesValueOverflow):
        SharesValue.from_uint256(value)


@given(
    total_pooled=st.integers(min_value=0),
    share=shares_value_strategy,
    total=shares_value_strategy.filter(lambda x: x != 0),
)
def test_calc_eth_value(total_pooled, share, total):
    expected = (total_pooled * share) // total
    eth_value: ETHValue

    if expected > SharesValue.MAX_VALUE:
        with pytest.raises(ETHValueOverflow):
            eth_value = SharesValue.calc_eth_value(
                ETHValue.from_uint256(total_pooled), SharesValue.from_uint256(share), SharesValue.from_uint256(total)
            )
    else:
        eth_value = SharesValue.calc_eth_value(
            ETHValue.from_uint256(total_pooled), SharesValue.from_uint256(share), SharesValue.from_uint256(total)
        )
        assert eth_value.value == expected


@given(v1=shares_value_strategy, v2=shares_value_strategy)
def test_add(v1, v2):
    shares_value1 = SharesValue.from_uint256(v1)
    shares_value2 = SharesValue.from_uint256(v2)

    if (v1 + v2) > 2**128 - 1:
        pytest.raises(SharesValueOverflow)
    else:
        result = shares_value1 + shares_value2
        assert result.value == v1 + v2


@given(v1=shares_value_strategy, v2=shares_value_strategy)
def test_sub(v1, v2):
    shares_value1 = SharesValue.from_uint256(v1)
    shares_value2 = SharesValue.from_uint256(v2)
    if v1 >= v2:
        result = shares_value1 - shares_value2
        assert result.value == v1 - v2
    else:
        with pytest.raises(SharesValueUnderflow):
            shares_value1 - shares_value2


@given(v1=shares_value_strategy, v2=shares_value_strategy)
def test_lt(v1, v2):
    shares_value1 = SharesValue.from_uint256(v1)
    shares_value2 = SharesValue.from_uint256(v2)
    assert (shares_value1 < shares_value2) == (v1 < v2)


@given(v1=shares_value_strategy, v2=shares_value_strategy)
def test_gt(v1, v2):
    shares_value1 = SharesValue.from_uint256(v1)
    shares_value2 = SharesValue.from_uint256(v2)
    assert (shares_value1 > shares_value2) == (v1 > v2)


@given(v1=shares_value_strategy, v2=shares_value_strategy)
def test_eq(v1, v2):
    shares_value1 = SharesValue.from_uint256(v1)
    shares_value2 = SharesValue.from_uint256(v2)
    assert (shares_value1 == shares_value2) == (v1 == v2)


@given(v1=shares_value_strategy, v2=shares_value_strategy)
def test_ne(v1, v2):
    shares_value1 = SharesValue.from_uint256(v1)
    shares_value2 = SharesValue.from_uint256(v2)
    assert (shares_value1 != shares_value2) == (v1 != v2)


@given(shares_value_strategy)
def test_to_uint256(value):
    shares_value = SharesValue.from_uint256(value)
    assert shares_value.to_uint256() == value


def test_constants():
    assert SharesValue.ZERO == 0
    assert SharesValue.MAX_VALUE == 2**128 - 1

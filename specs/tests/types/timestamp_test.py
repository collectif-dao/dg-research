from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.types.timestamp import Timestamp, Timestamps

timestamp_value_strategy = st.integers(min_value=0, max_value=Timestamp.MAX_VALUE)


@given(timestamp_value_strategy)
def test_initialization(value):
    ts = Timestamp(value)
    assert ts.value == value


@given(st.integers().filter(lambda x: x < 0 or x > Timestamp.MAX_VALUE))
def test_out_of_bounds(value):
    with pytest.raises(ValueError):
        Timestamp(value)


@given(
    timestamp_value_strategy,
    timestamp_value_strategy,
)
def test_comparisons(value1, value2):
    ts1 = Timestamp(value1)
    ts2 = Timestamp(value2)

    assert (ts1 < ts2) == (value1 < value2)
    assert (ts1 > ts2) == (value1 > value2)
    assert (ts1 <= ts2) == (value1 <= value2)
    assert (ts1 >= ts2) == (value1 >= value2)
    assert (ts1 == ts2) == (value1 == value2)
    assert (ts1 != ts2) == (value1 != value2)


@given(timestamp_value_strategy)
def test_is_zero(value):
    ts = Timestamp(value)
    assert ts.is_zero() == (value == 0)
    assert ts.is_not_zero() == (value != 0)


@given(timestamp_value_strategy)
def test_to_seconds(value):
    ts = Timestamp(value)
    assert ts.to_seconds() == value


@given(timestamp_value_strategy)
def test_from_uint256(value):
    ts = Timestamp.from_uint256(value)
    assert ts.value == value


@given(st.integers(min_value=Timestamp.MAX_VALUE + 1))
def test_from_uint256_overflow(value):
    with pytest.raises(ValueError):
        Timestamp.from_uint256(value)


def test_now():
    now_ts = Timestamp.now()
    now_time = int(datetime.now().timestamp())
    assert now_ts.value == pytest.approx(now_time, abs=1)


@given(timestamp_value_strategy)
def test_frozen(value):
    ts = Timestamp(value)
    with pytest.raises(FrozenInstanceError):
        ts.value = value + 1


def test_constants():
    assert Timestamps.ZERO.value == 0
    assert Timestamps.MIN.value == 0
    assert Timestamps.MAX.value == Timestamp.MAX_VALUE


def test_now_static():
    now_ts = Timestamps.now()
    now_time = int(datetime.now().timestamp())
    assert now_ts.value == pytest.approx(now_time, abs=1)


@given(timestamp_value_strategy)
def test_from_uint256_static(value):
    ts = Timestamps.from_uint256(value)
    assert ts.value == value


@given(st.integers(min_value=Timestamp.MAX_VALUE + 1))
def test_from_uint256_static_overflow(value):
    with pytest.raises(ValueError):
        Timestamps.from_uint256(value)

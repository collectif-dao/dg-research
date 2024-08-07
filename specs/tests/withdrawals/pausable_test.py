import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp, Timestamps
from specs.withdrawals.pausable import Pausable


def test_initialization():
    pausable = Pausable()
    time_manager = TimeManager()
    time_manager.initialize()

    pausable.initialize(time_manager)
    assert pausable.time_manager == time_manager


@given(st.integers(min_value=1, max_value=315500000))
def test_pause_for(duration):
    pausable = Pausable()
    time_manager = TimeManager()
    time_manager.initialize()

    pausable.initialize(time_manager)

    with pytest.raises(Exception, match="ZeroPauseDuration"):
        pausable._pause_for(Timestamps.ZERO)

    pausable._pause_for(Timestamp(duration))

    current_timestamp = time_manager.get_current_timestamp_value()

    assert pausable.resume_since_timestamp == current_timestamp + Timestamp(duration)


@given(st.integers(min_value=1, max_value=315500000))
def test_pause_until(duration):
    pausable = Pausable()
    time_manager = TimeManager()
    time_manager.initialize()

    pausable.initialize(time_manager)

    target_timestamp = time_manager.get_current_timestamp_value() + Timestamp(duration)

    with pytest.raises(Exception, match="PauseUntilMustBeInFuture"):
        pausable._pause_until(Timestamp(duration))

    pausable._pause_until(target_timestamp)
    assert pausable.resume_since_timestamp == target_timestamp + Timestamp(1)


@given(st.integers(min_value=1, max_value=315500000))
def test_resume(duration):
    pausable = Pausable()
    time_manager = TimeManager()
    time_manager.initialize()
    pausable.initialize(time_manager)

    pausable._pause_for(Timestamp(duration))
    pausable._resume()

    assert pausable.resume_since_timestamp == time_manager.get_current_timestamp_value()

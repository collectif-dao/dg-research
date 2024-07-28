import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.dual_governance.emergency_protection import EmergencyProtection
from specs.tests.accounting_test import ethereum_address_strategy
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp, Timestamps


def limited_time_strategy():
    return st.integers(min_value=0, max_value=30802118400)


@given(
    activation_committee=ethereum_address_strategy(),
    execution_committee=ethereum_address_strategy(),
    protection_duration=limited_time_strategy(),
    emergency_mode_duration=limited_time_strategy(),
)
def test_setup(
    activation_committee,
    execution_committee,
    protection_duration,
    emergency_mode_duration,
):
    time_manager = TimeManager()
    time_manager.initialize()

    emergency_protection = EmergencyProtection()

    emergency_protection.setup(
        activation_committee,
        execution_committee,
        Timestamp(protection_duration),
        Timestamp(emergency_mode_duration),
        time_manager,
    )

    assert emergency_protection.activation_committee == activation_committee
    assert emergency_protection.execution_committee == execution_committee
    assert (
        emergency_protection.protected_till
        == Timestamp(protection_duration) + time_manager.get_current_timestamp_value()
    )
    assert emergency_protection.emergency_mode_duration == Timestamp(emergency_mode_duration)
    assert emergency_protection.time_manager == time_manager


@given(
    activation_committee=ethereum_address_strategy(),
    execution_committee=ethereum_address_strategy(),
    protection_duration=limited_time_strategy(),
    emergency_mode_duration=limited_time_strategy(),
)
def test_activate(activation_committee, execution_committee, protection_duration, emergency_mode_duration):
    time_manager = TimeManager()
    time_manager.initialize()

    emergency_protection = EmergencyProtection()
    emergency_protection.setup(
        activation_committee,
        execution_committee,
        Timestamp(protection_duration),
        Timestamp(emergency_mode_duration),
        time_manager,
    )

    timestamp_now = time_manager.get_current_timestamp_value()

    if timestamp_now <= emergency_protection.protected_till:
        emergency_protection.activate()
        assert emergency_protection.emergency_mode_ends_after == timestamp_now + Timestamp(emergency_mode_duration)
    else:
        with pytest.raises(Exception, match="EmergencyCommitteeExpired"):
            emergency_protection.activate()


@given(
    activation_committee=ethereum_address_strategy(),
    execution_committee=ethereum_address_strategy(),
    protection_duration=limited_time_strategy(),
    emergency_mode_duration=limited_time_strategy(),
)
def test_deactivate(activation_committee, execution_committee, protection_duration, emergency_mode_duration):
    time_manager = TimeManager()
    time_manager.initialize()

    emergency_protection = EmergencyProtection()
    emergency_protection.setup(
        activation_committee,
        execution_committee,
        Timestamp(protection_duration),
        Timestamp(emergency_mode_duration),
        time_manager,
    )
    emergency_protection.deactivate()

    assert emergency_protection.activation_committee is None
    assert emergency_protection.execution_committee is None
    assert emergency_protection.protected_till == Timestamps.ZERO
    assert emergency_protection.emergency_mode_ends_after == Timestamps.ZERO
    assert emergency_protection.emergency_mode_duration == Timestamps.ZERO


@given(
    activation_committee=ethereum_address_strategy(),
    execution_committee=ethereum_address_strategy(),
    protection_duration=limited_time_strategy(),
    emergency_mode_duration=limited_time_strategy(),
)
def test_is_emergency_mode_activated(
    activation_committee,
    execution_committee,
    protection_duration,
    emergency_mode_duration,
):
    time_manager = TimeManager()
    time_manager.initialize()
    emergency_protection = EmergencyProtection()
    emergency_protection.setup(
        activation_committee,
        execution_committee,
        Timestamp(protection_duration),
        Timestamp(emergency_mode_duration),
        time_manager,
    )

    timestamp_now = time_manager.get_current_timestamp_value()

    if timestamp_now <= emergency_protection.protected_till:
        emergency_protection.activate()
        assert emergency_protection.is_emergency_mode_activated()
    else:
        assert not emergency_protection.is_emergency_mode_activated()


@given(
    activation_committee=ethereum_address_strategy(),
    execution_committee=ethereum_address_strategy(),
    protection_duration=limited_time_strategy(),
    emergency_mode_duration=limited_time_strategy(),
)
def test_is_emergency_mode_passed(
    activation_committee,
    execution_committee,
    protection_duration,
    emergency_mode_duration,
):
    time_manager = TimeManager()
    time_manager.initialize()
    emergency_protection = EmergencyProtection()
    emergency_protection.setup(
        activation_committee,
        execution_committee,
        Timestamp(protection_duration),
        Timestamp(emergency_mode_duration),
        time_manager,
    )

    timestamp_now = time_manager.get_current_timestamp_value()

    if timestamp_now <= emergency_protection.protected_till:
        emergency_protection.activate()
        assert not emergency_protection.is_emergency_mode_passed()
        time_manager.shift_current_timestamp(Timestamp(emergency_mode_duration + 1))
        assert emergency_protection.is_emergency_mode_passed()
    else:
        assert not emergency_protection.is_emergency_mode_passed()


@given(
    activation_committee=ethereum_address_strategy(),
    execution_committee=ethereum_address_strategy(),
    protection_duration=limited_time_strategy(),
    emergency_mode_duration=limited_time_strategy(),
)
def test_is_emergency_protection_enabled(
    activation_committee,
    execution_committee,
    protection_duration,
    emergency_mode_duration,
):
    time_manager = TimeManager()
    time_manager.initialize()
    emergency_protection = EmergencyProtection()
    emergency_protection.setup(
        activation_committee,
        execution_committee,
        Timestamp(protection_duration),
        Timestamp(emergency_mode_duration),
        time_manager,
    )

    timestamp_now = time_manager.get_current_timestamp_value()

    if timestamp_now <= emergency_protection.protected_till:
        assert emergency_protection.is_emergency_protection_enabled()
        emergency_protection.activate()
        assert emergency_protection.is_emergency_protection_enabled()
    else:
        assert not emergency_protection.is_emergency_protection_enabled()


@given(
    activation_committee=ethereum_address_strategy(),
    account=ethereum_address_strategy(),
)
def test_check_activation_committee(
    activation_committee,
    account,
):
    time_manager = TimeManager()
    time_manager.initialize()

    emergency_protection = EmergencyProtection()
    emergency_protection.setup(
        activation_committee,
        "",
        Timestamp(0),
        Timestamp(0),
        time_manager,
    )

    if activation_committee != account:
        with pytest.raises(Exception, match="NotEmergencyActivator"):
            emergency_protection.check_activation_committee(account)
    else:
        emergency_protection.check_activation_committee(account)


@given(
    execution_committee=ethereum_address_strategy(),
    account=ethereum_address_strategy(),
)
def test_check_execution_committee(
    execution_committee,
    account,
):
    time_manager = TimeManager()
    time_manager.initialize()

    emergency_protection = EmergencyProtection()
    emergency_protection.setup(
        "",
        execution_committee,
        Timestamp(0),
        Timestamp(0),
        time_manager,
    )

    if execution_committee != account:
        with pytest.raises(Exception, match="NotEmergencyEnactor"):
            emergency_protection.check_execution_committee(account)
    else:
        emergency_protection.check_execution_committee(account)


@given(
    activation_committee=ethereum_address_strategy(),
    execution_committee=ethereum_address_strategy(),
    protection_duration=limited_time_strategy(),
    emergency_mode_duration=limited_time_strategy(),
    expected=st.booleans(),
)
def test_check_emergency_mode_status(
    activation_committee,
    execution_committee,
    protection_duration,
    emergency_mode_duration,
    expected,
):
    time_manager = TimeManager()
    time_manager.initialize()

    emergency_protection = EmergencyProtection()
    emergency_protection.setup(
        activation_committee,
        execution_committee,
        Timestamp(protection_duration),
        Timestamp(emergency_mode_duration),
        time_manager,
    )

    timestamp_now = time_manager.get_current_timestamp_value()

    if timestamp_now <= emergency_protection.protected_till:
        emergency_protection.activate()
        actual = emergency_protection.is_emergency_mode_activated()
    else:
        actual = False

    if actual != expected:
        with pytest.raises(Exception, match="InvalidEmergencyModeStatus"):
            emergency_protection.check_emergency_mode_status(expected)
    else:
        emergency_protection.check_emergency_mode_status(expected)

from datetime import timedelta

from hypothesis import given
from hypothesis import strategies as st

from specs.committees.emergency_activation_committee import EmergencyActivationCommittee
from specs.dual_governance.timelock import EmergencyProtectedTimelock
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.committees.hash_consensus_test import hash_consensus_members_strategy
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp


@given(
    members=hash_consensus_members_strategy(3),
    timelock_duration=st.integers(min_value=1, max_value=315500000),
    address=ethereum_address_strategy(),
)
def test_approve_emergency_activate(members, timelock_duration, address):
    time_manager = TimeManager()
    time_manager.initialize()

    timelock = EmergencyProtectedTimelock()
    timelock.initialize(time_manager)

    committee = EmergencyActivationCommittee()
    committee.initialize(members, len(members), timelock_duration, time_manager, timelock, address)

    emergency_mode_duration = Timestamp.from_uint256(int(timedelta(days=1).total_seconds()))
    protection_duration = Timestamp.from_uint256(int(timedelta(days=10).total_seconds()))

    timelock.set_emergency_protection(
        address,
        "0x0",
        protection_duration,
        emergency_mode_duration,
    )

    for member in members:
        committee.approve_emergency_activate(member)

    support, quorum, executed = committee.get_emergency_activate_state()
    assert support == len(members)
    assert quorum == len(members)
    assert not executed


@given(
    members=hash_consensus_members_strategy(3),
    timelock_duration=st.integers(min_value=1, max_value=315500000),
    address=ethereum_address_strategy(),
)
def test_execute_emergency_activate(members, timelock_duration, address):
    time_manager = TimeManager()
    time_manager.initialize()

    timelock = EmergencyProtectedTimelock()
    timelock.initialize(time_manager)

    committee = EmergencyActivationCommittee()
    committee.initialize(members, len(members), timelock_duration, time_manager, timelock, address)

    emergency_mode_duration = Timestamp.from_uint256(int(timedelta(days=1).total_seconds()))

    protection = int(timedelta(days=10).total_seconds())

    protection_duration = Timestamp.from_uint256(timelock_duration + protection)

    timelock.set_emergency_protection(
        address,
        "0x0",
        protection_duration,
        emergency_mode_duration,
    )

    for member in members:
        committee.approve_emergency_activate(member)

    time_manager.shift_current_time(timedelta(seconds=(timelock_duration + 1)))

    committee.execute_emergency_activate()
    support, quorum, executed = committee.get_emergency_activate_state()
    assert executed

from datetime import timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from specs.committees.emergency_activation_committee import EmergencyActivationCommittee
from specs.committees.emergency_execution_committee import EmergencyExecutionCommittee
from specs.dual_governance.timelock import EmergencyProtectedTimelock
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.committees.hash_consensus_test import hash_consensus_members_strategy
from specs.tests.proposals_test import calls_strategy
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp


@given(
    members=hash_consensus_members_strategy(3),
    timelock_duration=st.integers(min_value=2592000, max_value=315500000),
    activation_address=ethereum_address_strategy(),
    execution_address=ethereum_address_strategy(),
    executor=ethereum_address_strategy(),
    calls=calls_strategy(),
)
@settings(deadline=None)
def test_emergency_execution(members, timelock_duration, activation_address, execution_address, executor, calls):
    time_manager = TimeManager()
    time_manager.initialize()

    timelock = EmergencyProtectedTimelock()
    timelock.initialize(time_manager)

    activation_committee = EmergencyActivationCommittee()
    activation_committee.initialize(
        members, len(members), timelock_duration, time_manager, timelock, activation_address
    )

    execution_committee = EmergencyExecutionCommittee()
    execution_committee.initialize(members, len(members), timelock_duration, time_manager, timelock, execution_address)

    emergency_duration = (timelock_duration * 2) + 10
    protection_duration = (timelock_duration * 3) + 10
    emergency_mode_duration = Timestamp.from_uint256(int(timedelta(seconds=emergency_duration).total_seconds()))
    protection_mode_duration = Timestamp.from_uint256(int(timedelta(seconds=protection_duration).total_seconds()))

    timelock.set_emergency_protection(
        activation_address,
        execution_address,
        protection_mode_duration,
        emergency_mode_duration,
    )

    proposal_id = timelock.submit(executor, calls)

    time_manager.shift_current_time(timedelta(seconds=(timelock.after_submit_delay + 10)))
    timelock.schedule(proposal_id)

    for member in members:
        activation_committee.approve_emergency_activate(member)

    time_manager.shift_current_time(timedelta(seconds=(timelock_duration + 1)))

    activation_committee.execute_emergency_activate()

    for member in members:
        execution_committee.vote_emergency_execute(proposal_id, member, True)

    support, quorum, executed = execution_committee.get_emergency_execute_state(proposal_id)
    assert support
    assert not executed

    time_manager.shift_current_time(timedelta(seconds=(timelock_duration + 1)))

    execution_committee.execute_emergency_execute(proposal_id)
    support, quorum, executed = execution_committee.get_emergency_execute_state(proposal_id)
    assert executed


@given(
    members=hash_consensus_members_strategy(3),
    timelock_duration=st.integers(min_value=864000, max_value=315500000),
    activation_address=ethereum_address_strategy(),
    execution_address=ethereum_address_strategy(),
)
@settings(deadline=None)
def test_emergency_reset_functions(members, timelock_duration, activation_address, execution_address):
    time_manager = TimeManager()
    time_manager.initialize()

    timelock = EmergencyProtectedTimelock()
    timelock.initialize(time_manager)

    activation_committee = EmergencyActivationCommittee()
    activation_committee.initialize(
        members, len(members), timelock_duration, time_manager, timelock, activation_address
    )

    execution_committee = EmergencyExecutionCommittee()
    execution_committee.initialize(members, len(members), timelock_duration, time_manager, timelock, execution_address)

    emergency_duration = (timelock_duration * 2) + 10
    protection_duration = (timelock_duration * 3) + 10
    emergency_mode_duration = Timestamp.from_uint256(int(timedelta(seconds=emergency_duration).total_seconds()))
    protection_mode_duration = Timestamp.from_uint256(int(timedelta(seconds=protection_duration).total_seconds()))

    timelock.set_emergency_protection(
        activation_address,
        execution_address,
        protection_mode_duration,
        emergency_mode_duration,
    )

    for member in members:
        activation_committee.approve_emergency_activate(member)

    time_manager.shift_current_time(timedelta(seconds=(timelock_duration + 1)))

    activation_committee.execute_emergency_activate()

    for member in members:
        execution_committee.approve_emergency_reset(member)

    support, quorum, executed = execution_committee.get_emergency_reset_state()
    assert support == len(members)
    assert quorum == len(members)
    assert not executed

    time_manager.shift_current_time(timedelta(seconds=(timelock_duration + 1)))

    execution_committee.execute_emergency_reset()

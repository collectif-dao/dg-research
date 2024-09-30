import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.committees.hash_consensus import Errors, HashConsensus
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.emergency_protection_test import limited_time_strategy
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp


def hash_consensus_members_strategy(min_size: int = 1):
    return st.lists(ethereum_address_strategy(), min_size=min_size, max_size=10, unique=True)


@given(hash_consensus_members_strategy(), st.integers(min_value=1, max_value=10), limited_time_strategy())
def test_initialize(members, quorum, timelock_duration):
    time_manager = TimeManager()
    time_manager.initialize()
    consensus = HashConsensus()
    consensus.initialize(members, quorum, timelock_duration, time_manager)
    assert consensus.quorum == quorum
    assert consensus.timelock_duration == Timestamp(timelock_duration)
    assert set(consensus.get_members()) == set(members)


@given(hash_consensus_members_strategy(), limited_time_strategy())
def test_initialize_invalid_quorum(members, timelock_duration):
    time_manager = TimeManager()
    time_manager.initialize()
    consensus = HashConsensus()
    with pytest.raises(Errors.InvalidQuorum):
        consensus.initialize(members, 0, timelock_duration, time_manager)


@given(
    hash_consensus_members_strategy(),
    ethereum_address_strategy(),
    st.integers(min_value=1, max_value=10),
    limited_time_strategy(),
)
def test_add_member(members, new_member, new_quorum, timelock_duration):
    time_manager = TimeManager()
    time_manager.initialize()
    consensus = HashConsensus()
    consensus.initialize(members, len(members), timelock_duration, time_manager)

    if new_member in members:
        with pytest.raises(Errors.DuplicatedMember):
            consensus.add_member(new_member, len(members) + 1)
    else:
        if new_quorum > len(members) + 1:
            with pytest.raises(Errors.InvalidQuorum):
                consensus.add_member(new_member, new_quorum)
        else:
            consensus.add_member(new_member, new_quorum)
            assert new_member in consensus.get_members()
            assert consensus.quorum == new_quorum


@given(
    hash_consensus_members_strategy(),
    ethereum_address_strategy(),
    st.integers(min_value=1, max_value=10),
    limited_time_strategy(),
)
def test_remove_member(members, member_to_remove, new_quorum, timelock_duration):
    time_manager = TimeManager()
    time_manager.initialize()
    consensus = HashConsensus()

    if member_to_remove not in members:
        consensus.initialize(members + [member_to_remove], len(members) + 1, timelock_duration, time_manager)

        if new_quorum <= len(members):
            consensus.remove_member(member_to_remove, new_quorum)
            assert member_to_remove not in consensus.get_members()
            assert consensus.quorum == new_quorum

            with pytest.raises(Errors.IsNotMember):
                consensus.remove_member(member_to_remove, len(members) - 2)

        else:
            with pytest.raises(Errors.InvalidQuorum):
                consensus.remove_member(member_to_remove, new_quorum)

    else:
        with pytest.raises(Errors.DuplicatedMember):
            consensus.initialize(members + [member_to_remove], len(members) + 1, timelock_duration, time_manager)


@given(hash_consensus_members_strategy(), st.integers(min_value=0, max_value=25), limited_time_strategy())
def test_set_quorum_invalid(members, new_quorum, timelock_duration):
    time_manager = TimeManager()
    time_manager.initialize()
    consensus = HashConsensus()
    consensus.initialize(members, len(members), timelock_duration, time_manager)

    if new_quorum > len(members) or new_quorum == 0:
        with pytest.raises(Errors.InvalidQuorum):
            consensus.set_quorum(new_quorum)
    else:
        consensus.set_quorum(new_quorum)


@given(hash_consensus_members_strategy(), limited_time_strategy())
def test_set_timelock_duration(members, timelock_duration):
    time_manager = TimeManager()
    time_manager.initialize()
    consensus = HashConsensus()
    consensus.initialize(members, len(members), 10, time_manager)

    consensus.set_timelock_duration(timelock_duration)
    assert consensus.timelock_duration == Timestamp(timelock_duration)


@given(
    hash_consensus_members_strategy(3),
    ethereum_address_strategy(),
    st.text(min_size=5),
    st.booleans(),
    limited_time_strategy(),
)
def test_vote_and_mark_used(members, member, hash_str, support: bool, timelock_duration):
    time_manager = TimeManager()
    time_manager.initialize()
    consensus = HashConsensus()
    consensus.initialize(members, len(members), timelock_duration, time_manager)

    consensus.vote(member, hash_str, support)
    assert consensus.approves[member][hash_str] == support

    # Vote again with the same member and support
    consensus.vote(member, hash_str, support)
    assert consensus.approves[member][hash_str] == support

    # Vote again with different support
    consensus.vote(member, hash_str, not support)
    assert consensus.approves[member][hash_str] is not support

    # Check that quorum is not reached initially
    with pytest.raises(Errors.QuorumIsNotReached):
        consensus.mark_used(hash_str)

    # Reach quorum by voting with all members
    for m in members:
        consensus.vote(m, hash_str, True)
    assert consensus.hash_states[hash_str].quorum_at > Timestamp(0)

    # Attempt to mark used before timelock duration
    if timelock_duration != 0:
        with pytest.raises(Errors.TimelockNotPassed):
            consensus.mark_used(hash_str)

    # Shift time to pass the timelock duration period
    time_manager.shift_current_timestamp(Timestamp(timelock_duration + 10))

    consensus.mark_used(hash_str)
    assert consensus.hash_states[hash_str].used_at > Timestamp(0)

    with pytest.raises(Errors.HashAlreadyUsed):
        consensus.vote(member, hash_str, support)

    with pytest.raises(Errors.HashAlreadyUsed):
        consensus.mark_used(hash_str)

import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.committees.enumerable_proposals import Bytes32ToProposalMap
from specs.time_manager import TimeManager


@given(key=st.binary(min_size=32, max_size=32), proposal_type=st.integers(min_value=0), data=st.binary())
def test_push_and_contains(key, proposal_type, data):
    time_manager = TimeManager()
    time_manager.initialize()
    map = Bytes32ToProposalMap()
    map.setup(time_manager)

    assert map.push(key, proposal_type, data)
    assert map.contains(key)


@given(
    keys=st.lists(st.binary(min_size=32, max_size=32), min_size=1, max_size=10, unique=True),
    proposal_type=st.integers(min_value=0),
    data=st.binary(),
)
def test_length_and_at(keys, proposal_type, data):
    time_manager = TimeManager()
    time_manager.initialize()
    map = Bytes32ToProposalMap()
    map.setup(time_manager)

    for key in keys:
        map.push(key, proposal_type, data)

    assert map.length() == len(keys)

    for i in range(len(keys)):
        assert map.at(i) is not None


@given(key=st.binary(min_size=32, max_size=32), proposal_type=st.integers(min_value=0), data=st.binary())
def test_get(key, proposal_type, data):
    time_manager = TimeManager()
    time_manager.initialize()
    map = Bytes32ToProposalMap()
    map.setup(time_manager)

    map.push(key, proposal_type, data)
    proposal = map.get(key)

    assert proposal is not None
    assert proposal.proposal_type == proposal_type
    assert proposal.data == data


@given(
    keys=st.lists(st.binary(min_size=32, max_size=32), min_size=1, max_size=10, unique=True),
    proposal_type=st.integers(min_value=0),
    data=st.binary(),
    offset=st.integers(min_value=0),
    limit=st.integers(min_value=1),
)
def test_get_ordered_keys_subset(keys, proposal_type, data, offset, limit):
    time_manager = TimeManager()
    time_manager.initialize()
    map = Bytes32ToProposalMap()
    map.setup(time_manager)

    for key in keys:
        map.push(key, proposal_type, data)

    if offset >= len(keys):
        with pytest.raises(Exception, match="OffsetOutOfBounds"):
            map.get_ordered_keys_subset(offset, limit)
    else:
        subset = map.get_ordered_keys_subset(offset, limit)

        assert len(subset) <= limit
        assert subset == map.get_ordered_keys()[offset : offset + limit]

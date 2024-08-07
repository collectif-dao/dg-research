import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.committees.proposals_list import ProposalsList
from specs.time_manager import TimeManager


@given(key=st.binary(min_size=32, max_size=32), proposal_type=st.integers(min_value=0), data=st.binary())
def test_push_proposal(key, proposal_type, data):
    time_manager = TimeManager()
    time_manager.initialize()
    proposals_list = ProposalsList()
    proposals_list.setup(time_manager)

    proposals_list._push_proposal(key, proposal_type, data)

    assert proposals_list.get_proposal(key) is not None


@given(
    keys=st.lists(st.binary(min_size=32, max_size=32), min_size=1, max_size=10, unique=True),
    proposal_type=st.integers(min_value=0),
    data=st.binary(),
    offset=st.integers(min_value=0),
    limit=st.integers(min_value=1),
)
def test_get_proposals(keys, proposal_type, data, offset, limit):
    time_manager = TimeManager()
    time_manager.initialize()
    proposals_list = ProposalsList()
    proposals_list.setup(time_manager)

    for key in keys:
        proposals_list._push_proposal(key, proposal_type, data)

    if offset >= len(keys):
        with pytest.raises(Exception, match="OffsetOutOfBounds"):
            proposals_list.get_proposals(offset, limit)
    else:
        proposals = proposals_list.get_proposals(offset, limit)
        assert len(proposals) <= limit


@given(
    keys=st.lists(st.binary(min_size=32, max_size=32), min_size=1, max_size=10, unique=True),
    proposal_type=st.integers(min_value=0),
    data=st.binary(),
)
def test_get_proposal_at(keys, proposal_type, data):
    time_manager = TimeManager()
    time_manager.initialize()
    proposals_list = ProposalsList()
    proposals_list.setup(time_manager)

    for key in keys:
        proposals_list._push_proposal(key, proposal_type, data)

    for i in range(len(keys)):
        assert proposals_list.get_proposal_at(i) is not None


@given(
    keys=st.lists(st.binary(min_size=32, max_size=32), min_size=1, max_size=10, unique=True),
    proposal_type=st.integers(min_value=0),
    data=st.binary(),
    offset=st.integers(min_value=0),
    limit=st.integers(min_value=1),
)
def test_get_ordered_keys(keys, proposal_type, data, offset, limit):
    time_manager = TimeManager()
    time_manager.initialize()
    proposals_list = ProposalsList()
    proposals_list.setup(time_manager)

    for key in keys:
        proposals_list._push_proposal(key, proposal_type, data)

    if offset >= len(keys):
        with pytest.raises(Exception, match="OffsetOutOfBounds"):
            proposals_list.get_ordered_keys(offset, limit)
    else:
        ordered_keys = proposals_list.get_ordered_keys(offset, limit)
        assert len(ordered_keys) <= limit

from datetime import timedelta
from typing import List

import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.dual_governance.proposals import ExecutorCall, ProposalErrors, Proposals, ProposalStatus
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.log import setup_logger
from specs.time_manager import TimeManager

logger = setup_logger()


def calls_strategy(min_size: int = 1):
    return st.lists(st.builds(ExecutorCall, st.text(), st.integers(), st.binary()), min_size=min_size)


def generate_multiple_proposals():
    return st.tuples(st.lists(ethereum_address_strategy()), st.lists(calls_strategy())).map(
        lambda t: (t[0][: len(t[0])], t[1][: len(t[0])])
    )


def test_initialize():
    time_manager = TimeManager()
    time_manager.initialize()
    proposals = Proposals()
    proposals.initialize(time_manager)

    assert proposals.state.last_cancelled_proposal_id == 0
    assert proposals.proposal_id_offset == 1
    assert len(proposals.state.proposals) == 0


@given(ethereum_address_strategy(), calls_strategy())
def test_submit(executor, calls):
    time_manager = TimeManager()
    time_manager.initialize()
    proposals = Proposals()
    proposals.initialize(time_manager)

    proposals_length = len(proposals.state.proposals)

    proposal_id = proposals.submit(executor, calls)
    proposal = proposals.get(proposal_id)

    assert len(proposals.state.proposals) > proposals_length
    assert proposal.id == proposal_id
    assert proposal.status == ProposalStatus.Submitted
    assert proposal.calls == calls
    assert proposal.executor == executor


@given(ethereum_address_strategy(), calls_strategy())
def test_schedule(executor, calls):
    time_manager = TimeManager()
    time_manager.initialize()
    proposals = Proposals()
    proposals.initialize(time_manager)

    after_submit_delay = int(timedelta(minutes=9).total_seconds())

    proposal_id = proposals.submit(executor, calls)

    assert proposals.can_schedule(proposal_id, after_submit_delay) is not True
    with pytest.raises(ProposalErrors.AfterSubmitDelayNotPassed):
        proposals.schedule(proposal_id, after_submit_delay)

    time_manager.shift_current_time(timedelta(minutes=10))

    assert proposals.can_schedule(proposal_id, after_submit_delay) is True
    proposals.schedule(proposal_id, after_submit_delay)

    proposal = proposals.get(proposal_id)
    assert proposal.status == ProposalStatus.Scheduled


@given(ethereum_address_strategy(), calls_strategy())
def test_execute(executor, calls):
    time_manager = TimeManager()
    time_manager.initialize()
    proposals = Proposals()
    proposals.initialize(time_manager)

    after_submit_delay = int(timedelta(minutes=9).total_seconds())

    proposal_id = proposals.submit(executor, calls)

    assert proposals.can_schedule(proposal_id, after_submit_delay) is not True
    with pytest.raises(ProposalErrors.AfterSubmitDelayNotPassed):
        proposals.schedule(proposal_id, after_submit_delay)

    time_manager.shift_current_time(timedelta(minutes=10))

    assert proposals.can_schedule(proposal_id, after_submit_delay) is True
    proposals.schedule(proposal_id, after_submit_delay)

    after_schedule_delay = int(timedelta(hours=12).total_seconds())

    assert proposals.can_execute(proposal_id, after_schedule_delay) is not True
    with pytest.raises(ProposalErrors.AfterScheduleDelayNotPassed):
        proposals.execute(proposal_id, after_schedule_delay)

    time_manager.shift_current_time(timedelta(hours=13))
    assert proposals.can_execute(proposal_id, after_schedule_delay) is True
    proposals.execute(proposal_id, after_schedule_delay)

    proposal = proposals.get(proposal_id)
    assert proposal.status == ProposalStatus.Executed


@given(generate_multiple_proposals())
def test_cancel_all(params):
    time_manager = TimeManager()
    time_manager.initialize()
    proposals = Proposals()
    proposals.initialize(time_manager)

    holders: List[str] = params[0]
    calls: List[ExecutorCall] = params[1]
    last_proposal_id: int = 0

    if len(holders) == len(calls):
        for i in range(len(holders)):
            holder = holders[i]
            proposal_calls = calls[i]

            last_proposal_id = proposals.submit(holder, proposal_calls)

        assert last_proposal_id == len(proposals.state.proposals)

        proposals.cancel_all()

        assert proposals.state.last_cancelled_proposal_id == last_proposal_id

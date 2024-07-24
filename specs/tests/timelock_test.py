from datetime import timedelta

import pytest
from hypothesis import given

from specs.dual_governance.proposals import ProposalErrors, ProposalStatus
from specs.dual_governance.timelock import EmergencyProtectedTimelock
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.log import setup_logger
from specs.tests.proposals_test import calls_strategy
from specs.time_manager import TimeManager

logger = setup_logger()


def test_initialize():
    time_manager = TimeManager()
    time_manager.initialize()
    timelock = EmergencyProtectedTimelock()
    timelock.initialize(time_manager)

    assert timelock.after_schedule_delay == int(timedelta(days=2).total_seconds())
    assert timelock.after_submit_delay == int(timedelta(days=3).total_seconds())

    proposals = timelock.proposals
    assert proposals.state.last_canceled_proposal_id == 0
    assert proposals.proposal_id_offset == 1
    assert len(proposals.state.proposals) == 0


@given(ethereum_address_strategy(), calls_strategy())
def test_proposals_functions(executor, calls):
    time_manager = TimeManager()
    time_manager.initialize()
    timelock = EmergencyProtectedTimelock()
    timelock.initialize(time_manager)

    proposal_id = timelock.submit(executor, calls)
    assert timelock.get_proposal_status(proposal_id) == ProposalStatus.Submitted

    assert timelock.can_schedule(proposal_id) is not True
    with pytest.raises(ProposalErrors.AfterSubmitDelayNotPassed):
        timelock.schedule(proposal_id)

    time_manager.shift_current_time(timedelta(timelock.after_submit_delay + 10))
    assert timelock.can_schedule(proposal_id) is True

    timelock.schedule(proposal_id)

    assert timelock.get_proposal_status(proposal_id) == ProposalStatus.Scheduled

    assert timelock.can_execute(proposal_id) is not True
    with pytest.raises(ProposalErrors.AfterScheduleDelayNotPassed):
        timelock.execute(proposal_id)

    time_manager.shift_current_time(timedelta(timelock.after_schedule_delay + 10))
    assert timelock.can_execute(proposal_id) is True

    timelock.execute(proposal_id)

    assert timelock.get_proposal_status(proposal_id) == ProposalStatus.Executed

    timelock.cancel_all_non_executed_proposals()

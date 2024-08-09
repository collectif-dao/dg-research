from datetime import timedelta

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from specs.dual_governance import DualGovernance, State
from specs.dual_governance.errors import Errors
from specs.dual_governance.proposals import ProposalStatus
from specs.escrow.escrow import Escrow, EscrowState
from specs.lido import Lido
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.log import setup_logger
from specs.tests.proposals_test import calls_strategy
from specs.time_manager import TimeManager
from specs.types.address import Address
from specs.types.shares_value import SharesValue
from specs.types.timestamp import Timestamp, Timestamps

from .utils import calc_rage_quit_support, sample_stETH_total_supply, test_escrow_address

logger = setup_logger()


def test_initialize():
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    dual_governance = DualGovernance()
    dual_governance.initialize(test_escrow_address, time_manager, lido)

    assert dual_governance.state.state == State.Normal
    assert dual_governance.state.entered_at == Timestamps.ZERO
    assert dual_governance.state.veto_signalling_activation_time == Timestamps.ZERO
    assert dual_governance.state.veto_signalling_reactivation_time == Timestamps.ZERO
    assert dual_governance.state.last_adoptable_state_exited_at == Timestamps.ZERO
    assert dual_governance.state.rage_quit_round == 0
    assert dual_governance.state.rage_quit_escrow is None

    escrow = dual_governance.state.signalling_escrow

    assert escrow.address == test_escrow_address
    assert escrow.state == EscrowState.SignallingEscrow
    assert escrow.rage_quit_extension_delay == Timestamps.ZERO
    assert escrow.rage_quit_withdrawals_timelock == Timestamps.ZERO

    assert dual_governance.timelock.after_schedule_delay == int(timedelta(days=2).total_seconds())
    assert dual_governance.timelock.after_submit_delay == int(timedelta(days=3).total_seconds())

    proposals = dual_governance.timelock.proposals
    assert proposals.state.last_canceled_proposal_id == 0
    assert proposals.proposal_id_offset == 1
    assert len(proposals.state.proposals) == 0


@given(
    ethereum_address_strategy(),
    calls_strategy(),
    st.integers(min_value=1, max_value=155_000 * 10**18),
)
@settings(deadline=None)
def test_proposals_submission_and_state_transition(holder_addr, calls, lock):
    assume(holder_addr != Address.ZERO)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    dual_governance = DualGovernance()
    dual_governance.initialize(test_escrow_address, time_manager, lido)

    escrow: Escrow = dual_governance.state.signalling_escrow
    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares

    proposal_id = dual_governance.timelock.submit(holder_addr, calls)
    assert dual_governance.timelock.get_proposal_status(proposal_id) == ProposalStatus.Submitted

    lido._mint_shares(holder_addr, lock)
    lido.set_buffered_ether(lido.get_buffered_ether() + lock)
    lido.approve(holder_addr, test_escrow_address, lock)

    escrow.lock_stETH(holder_addr, lock)
    assert total_locked_shares < escrow.accounting.state.stETHTotals.lockedShares

    rage_quit_support = calc_rage_quit_support(escrow)

    time_manager.shift_current_time(timedelta(dual_governance.timelock.after_submit_delay + 10))

    if rage_quit_support > dual_governance.state.config.first_seal_rage_quit_support:
        assert dual_governance.get_current_state() == State.VetoSignalling
        assert dual_governance.can_schedule(proposal_id) is not True

        with pytest.raises(Errors.ProposalsAdoptionSuspended):
            dual_governance.schedule_proposal(proposal_id)

        if rage_quit_support < dual_governance.state.config.second_seal_rage_quit_support:
            dual_governance.activate_next_state()
            assert dual_governance.get_current_state() == State.VetoSignallingDeactivation

            with pytest.raises(Errors.ProposalsCreationSuspended):
                dual_governance.submit_proposal(holder_addr, calls)

            time_manager.shift_current_timestamp(
                dual_governance.state.config.dynamic_timelock_max_duration + Timestamp(10)
            )
            dual_governance.schedule_proposal(proposal_id)
            assert dual_governance.get_current_state() == State.VetoCooldown

            escrow.unlock_stETH(holder_addr)
            assert escrow.accounting.state.assets[holder_addr].stETHLockedShares == SharesValue.from_uint256(0)

            assert dual_governance.can_execute(proposal_id) is not True

            time_manager.shift_current_time(timedelta(dual_governance.timelock.after_schedule_delay + 1))
            assert dual_governance.can_execute(proposal_id) is True
            dual_governance.timelock.execute(proposal_id)

            time_manager.shift_current_timestamp(dual_governance.state.config.veto_cooldown_duration + Timestamp(10))
            dual_governance.activate_next_state()
            assert dual_governance.get_current_state() == State.Normal

        elif rage_quit_support > dual_governance.state.config.second_seal_rage_quit_support:
            dual_governance.activate_next_state()
            assert dual_governance.get_current_state() == State.RageQuit
            dual_governance.cancel_all_pending_proposals()

    else:
        assert dual_governance.can_schedule(proposal_id) is True
        assert dual_governance.get_current_state() == State.Normal

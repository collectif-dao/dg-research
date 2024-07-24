from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from specs.dual_governance.config import DualGovernanceConfig
from specs.dual_governance.errors import Errors
from specs.dual_governance.state import DualGovernanceState, State
from specs.escrow.escrow import Escrow, EscrowState
from specs.lido import Lido
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.log import setup_logger
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp, Timestamps

from .utils import calc_rage_quit_support, sample_stETH_total_supply, test_escrow_address

logger = setup_logger()


def test_initialize():
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)
    time_manager = TimeManager()
    time_manager.initialize()
    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, sample_stETH_total_supply, time_manager, lido=lido)

    assert dgState.state == State.Normal
    assert dgState.entered_at == datetime.min
    assert dgState.veto_signalling_activation_time == datetime.min
    assert dgState.veto_signalling_reactivation_time == datetime.min
    assert dgState.last_adoptable_state_exited_at == datetime.min
    assert dgState.rage_quit_round == 0
    assert dgState.rage_quit_escrow is None

    escrow = dgState.signalling_escrow

    assert escrow.MASTER_COPY == test_escrow_address
    assert escrow.state == EscrowState.SignallingEscrow
    assert escrow.total_supply == sample_stETH_total_supply
    assert escrow.rage_quit_extension_delay == Timestamps.ZERO
    assert escrow.rage_quit_withdrawals_timelock == Timestamps.ZERO


@given(ethereum_address_strategy(), st.integers(min_value=1, max_value=155_000 * 10**18))
@settings(deadline=None)
def test_state_transitions(holder_addr, lock):
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)
    time_manager = TimeManager()
    time_manager.initialize()
    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, sample_stETH_total_supply, time_manager, lido=lido)

    with pytest.raises(Errors.ResealIsNotAllowedInNormalState):
        dgState.check_reseal_state()

    escrow: Escrow = dgState.signalling_escrow
    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares

    escrow.lock_stETH(holder_addr, lock)
    assert total_locked_shares < escrow.accounting.state.stETHTotals.lockedShares

    config: DualGovernanceConfig = dgState.config

    rage_quit_support = calc_rage_quit_support(escrow)

    if rage_quit_support > dgState.config.first_seal_rage_quit_support:
        dgState.activate_next_state()
        assert dgState.entered_at.replace(microsecond=0) == datetime.now().replace(microsecond=0)
        assert dgState.state == State.VetoSignalling
        assert dgState.veto_signalling_activation_time.replace(microsecond=0) == datetime.now().replace(microsecond=0)

        with pytest.raises(Errors.ProposalsAdoptionSuspended):
            dgState.check_can_schedule_proposal(datetime.now())
        with pytest.raises(Errors.ProposalsAdoptionSuspended):
            dgState.check_proposals_adoption_allowed()

        timelock_duration = dgState._calc_dynamic_timelock_duration(rage_quit_support)

        time_manager.shift_current_time(timelock_duration - timedelta(minutes=1))

        dgState.activate_next_state()

        # Still Veto Signaling state
        assert dgState.state == State.VetoSignalling

        time_manager.shift_current_time(timedelta(minutes=2))
        dgState.activate_next_state()

        if rage_quit_support < dgState.config.second_seal_rage_quit_support:
            assert dgState.state == State.VetoSignallingDeactivation
            assert dgState.entered_at.replace(microsecond=0) == time_manager.get_current_time().replace(microsecond=0)

            with pytest.raises(Errors.ProposalsCreationSuspended):
                dgState.check_proposals_creation_allowed()
            with pytest.raises(Errors.ProposalsAdoptionSuspended):
                dgState.check_proposals_adoption_allowed()

            # Increase time up to Veto Cooldown state
            time_manager.shift_current_time(
                dgState.config.veto_signalling_deactivation_max_duration + timedelta(minutes=1)
            )

            dgState.activate_next_state()

            assert dgState.state == State.VetoCooldown
            with pytest.raises(Errors.ProposalsCreationSuspended):
                dgState.check_proposals_creation_allowed()

            # Increase some time but stay within Veto Cooldown
            time_manager.shift_current_time(dgState.config.veto_cooldown_duration - timedelta(hours=1))

            dgState.activate_next_state()

            assert dgState.state == State.VetoCooldown

            # Increase some time but stay within Veto Cooldown
            time_manager.shift_current_time(timedelta(hours=2))

            dgState.activate_next_state()

            assert dgState.state == State.VetoSignalling
            assert dgState.entered_at.replace(microsecond=0) == time_manager.get_current_time().replace(microsecond=0)
            assert dgState.last_adoptable_state_exited_at.replace(
                microsecond=0
            ) == time_manager.get_current_time().replace(microsecond=0)
            assert dgState.veto_signalling_activation_time.replace(
                microsecond=0
            ) == time_manager.get_current_time().replace(microsecond=0)

        elif rage_quit_support > dgState.config.second_seal_rage_quit_support:
            assert dgState.state == State.RageQuit
            assert dgState.entered_at.replace(microsecond=0) == time_manager.get_current_time().replace(microsecond=0)

            # with pytest.raises(Errors.NotTie): # TODO: add sealableWithdrawalBlockers into DG State Config
            #     dgState.check_tiebreak()

            rqEscrow = dgState.rage_quit_escrow
            sEscrow = dgState.signalling_escrow

            assert rqEscrow.total_supply == sEscrow.total_supply
            assert rqEscrow.state == EscrowState.RageQuitEscrow
            assert rqEscrow.rage_quit_extension_delay == Timestamp(config.rage_quit_extension_delay.total_seconds())
            assert rqEscrow.rage_quit_withdrawals_timelock == Timestamp(
                dgState._calc_rage_quit_withdrawals_timelock(dgState.rage_quit_round).total_seconds()
            )

            assert sEscrow.state == EscrowState.SignallingEscrow

    else:
        dgState.activate_next_state()
        assert dgState.state == State.Normal

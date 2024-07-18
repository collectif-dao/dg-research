from datetime import datetime, timedelta

import pytest
from specs.dual_governance.errors import Errors
from specs.dual_governance.state import DualGovernanceConfig, DualGovernanceState, State
from specs.escrow.escrow import Escrow, EscrowState
from freezegun import freeze_time
from hypothesis import given, settings
from hypothesis import strategies as st

from specs.tests.log import setup_logger

from .utils import calc_rage_quit_support, sample_stETH_total_supply, test_escrow_address

logger = setup_logger()


def add_time_and_move_to(time_now: datetime, time_to_add: timedelta):
    time_to_move: datetime = time_now + time_to_add

    return freeze_time(time_to_move)


def test_initialize():
    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, sample_stETH_total_supply, datetime.now())

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
    assert escrow.staked_stETH == 0
    assert escrow.finalized_ETH == 0
    assert escrow.total_supply == sample_stETH_total_supply
    assert escrow.rage_quit_extension_delay == 0
    assert escrow.rage_quit_withdrawals_timelock == 0


@given(st.integers(min_value=1, max_value=155_000))
@settings(deadline=None)
def test_state_transitions(lock):
    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, sample_stETH_total_supply, datetime.now())

    with pytest.raises(Errors.ResealIsNotAllowedInNormalState):
        dgState.check_reseal_state()

    escrow: Escrow = dgState.signalling_escrow
    staked_ETH: int = escrow.staked_stETH

    escrow.stake_stETH(lock)
    assert staked_ETH < escrow.staked_stETH

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

        prevTime = dgState.current_time

        #freezer = add_time_and_move_to(prevTime, (timelock_duration - timedelta(minutes=1)))
        #freezer.start()

        dgState.shift_current_time(timelock_duration - timedelta(minutes=1))

        dgState.activate_next_state()

        prevTime = dgState.current_time

        # Still Veto Signaling state
        assert dgState.state == State.VetoSignalling

        # Increase time up to VetoSignalingDeactivation
        #freezer = add_time_and_move_to(prevTime, timedelta(minutes=2))
        #freezer.start()
        dgState.shift_current_time(timedelta(minutes=2))
        dgState.activate_next_state()

        prevTime = dgState.current_time

        if rage_quit_support < dgState.config.second_seal_rage_quit_support:
            assert dgState.state == State.VetoSignallingDeactivation
            assert dgState.entered_at.replace(microsecond=0) == prevTime.replace(microsecond=0)
            with pytest.raises(Errors.ProposalsCreationSuspended):
                dgState.check_proposals_creation_allowed()
            with pytest.raises(Errors.ProposalsAdoptionSuspended):
                dgState.check_proposals_adoption_allowed()

            # Increase time up to Veto Cooldown state
            #freezer = add_time_and_move_to(
            #    prevTime, dgState.config.veto_signalling_deactivation_max_duration + timedelta(minutes=1)
            #)
            #freezer.start()
            dgState.shift_current_time(dgState.config.veto_signalling_deactivation_max_duration + timedelta(minutes=1))
            prevTime = dgState.current_time

            dgState.activate_next_state()

            assert dgState.state == State.VetoCooldown
            with pytest.raises(Errors.ProposalsCreationSuspended):
                dgState.check_proposals_creation_allowed()

            # Increase some time but stay within Veto Cooldown
            #freezer = add_time_and_move_to(prevTime, dgState.config.veto_cooldown_duration - timedelta(hours=1))
            #freezer.start()
            dgState.shift_current_time(dgState.config.veto_cooldown_duration - timedelta(hours=1))
            prevTime = dgState.current_time

            dgState.activate_next_state()

            assert dgState.state == State.VetoCooldown

            # Increase some time but stay within Veto Cooldown
            #freezer = add_time_and_move_to(prevTime, timedelta(hours=2))
            #freezer.start()
            dgState.shift_current_time(timedelta(hours=2))
            prevTime = dgState.current_time

            dgState.activate_next_state()

            assert dgState.state == State.VetoSignalling
            assert dgState.entered_at.replace(microsecond=0) == prevTime.replace(microsecond=0)
            assert dgState.last_adoptable_state_exited_at.replace(microsecond=0) == prevTime.replace(microsecond=0)
            assert dgState.veto_signalling_activation_time.replace(microsecond=0) == prevTime.replace(microsecond=0)

        elif rage_quit_support > dgState.config.second_seal_rage_quit_support:
            assert dgState.state == State.RageQuit
            assert dgState.entered_at.replace(microsecond=0) == prevTime.replace(microsecond=0)

            # with pytest.raises(Errors.NotTie): # TODO: add sealableWithdrawalBlockers into DG State Config
            #     dgState.check_tiebreak()

            rqEscrow = dgState.rage_quit_escrow
            sEscrow = dgState.signalling_escrow

            assert rqEscrow.total_supply == sEscrow.total_supply
            assert rqEscrow.state == EscrowState.RageQuitEscrow
            assert rqEscrow.staked_stETH > sEscrow.staked_stETH
            assert rqEscrow.rage_quit_extension_delay == config.rage_quit_extension_delay
            assert rqEscrow.rage_quit_withdrawals_timelock == dgState._calc_rage_quit_withdrawals_timelock(
                dgState.rage_quit_round
            )

            assert sEscrow.state == EscrowState.SignallingEscrow
            assert sEscrow.staked_stETH == 0
            assert sEscrow.finalized_ETH == 0

    else:
        dgState.activate_next_state()
        assert dgState.state == State.Normal

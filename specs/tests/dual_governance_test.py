from datetime import datetime, timedelta

from specs.dual_governance import DualGovernance, State
from specs.escrow.escrow import EscrowState
from specs.lido import Lido
from specs.tests.log import setup_logger
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamps

from .utils import sample_stETH_total_supply, test_escrow_address

logger = setup_logger()


def test_initialize():
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    time_manager = TimeManager()
    time_manager.initialize()

    dual_governance = DualGovernance()
    dual_governance.initialize(test_escrow_address, time_manager, lido)

    assert dual_governance.state.state == State.Normal
    assert dual_governance.state.entered_at == datetime.min
    assert dual_governance.state.veto_signalling_activation_time == datetime.min
    assert dual_governance.state.veto_signalling_reactivation_time == datetime.min
    assert dual_governance.state.last_adoptable_state_exited_at == datetime.min
    assert dual_governance.state.rage_quit_round == 0
    assert dual_governance.state.rage_quit_escrow is None

    escrow = dual_governance.state.signalling_escrow

    assert escrow.MASTER_COPY == test_escrow_address
    assert escrow.state == EscrowState.SignallingEscrow
    assert escrow.rage_quit_extension_delay == Timestamps.ZERO
    assert escrow.rage_quit_withdrawals_timelock == Timestamps.ZERO

    assert dual_governance.timelock.after_schedule_delay == int(timedelta(days=2).total_seconds())
    assert dual_governance.timelock.after_submit_delay == int(timedelta(days=3).total_seconds())

    proposals = dual_governance.timelock.proposals
    assert proposals.state.last_canceled_proposal_id == 0
    assert proposals.proposal_id_offset == 1
    assert len(proposals.state.proposals) == 0

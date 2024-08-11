from datetime import timedelta

from hypothesis import assume, given
from hypothesis import strategies as st

from specs.committees.tiebreaker_core import TiebreakerCore
from specs.dual_governance import DualGovernance
from specs.dual_governance.state import State
from specs.escrow.escrow import Escrow
from specs.lido import Lido
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.committees.hash_consensus_test import hash_consensus_members_strategy
from specs.tests.proposals_test import calls_strategy
from specs.tests.utils import calc_rage_quit_support, sample_stETH_total_supply, test_escrow_address
from specs.time_manager import TimeManager
from specs.types.address import Address
from specs.types.timestamp import Timestamp


@given(
    members=hash_consensus_members_strategy(3),
    timelock_duration=st.integers(min_value=1, max_value=315500000),
    tiebreaker_address=ethereum_address_strategy(),
    executor=ethereum_address_strategy(),
    calls=calls_strategy(),
    stETH_holder=ethereum_address_strategy(),
    lock=st.integers(min_value=155_000 * 10**18, max_value=195_000 * 10**18),
)
def test_schedule_proposal_workflow(
    members, timelock_duration, tiebreaker_address, executor, calls, stETH_holder, lock
):
    assume(
        stETH_holder != Address.ZERO
        and stETH_holder != Address.DEAD
        and stETH_holder != test_escrow_address
        and stETH_holder != executor
    )
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    dual_governance = DualGovernance()
    dual_governance.initialize(test_escrow_address, time_manager, lido)

    tiebreaker = TiebreakerCore()
    tiebreaker.initialize(members, len(members), timelock_duration, time_manager, dual_governance, tiebreaker_address)

    dual_governance.set_tiebreaker_protection(tiebreaker, None)

    proposal_id = dual_governance.timelock.submit(executor, calls)

    escrow: Escrow = dual_governance.state.signalling_escrow

    buffered_ether = lido.get_buffered_ether()

    lido._mint_shares(stETH_holder, lock)
    lido.set_buffered_ether(buffered_ether + lock)
    lido.approve(stETH_holder, test_escrow_address, lock)

    escrow.lock_stETH(stETH_holder, lock)

    rage_quit_support = calc_rage_quit_support(escrow)

    if rage_quit_support > dual_governance.state.config.second_seal_rage_quit_support:
        time_manager.shift_current_timestamp(dual_governance.state.config.dynamic_timelock_max_duration + Timestamp(1))
        dual_governance.activate_next_state()
        assert dual_governance.get_current_state() == State.RageQuit

        for member in members:
            tiebreaker.schedule_proposal(proposal_id, member)

        support, quorum, executed = tiebreaker.get_schedule_proposal_state(proposal_id)
        assert support == len(members)
        assert quorum == len(members)
        assert not executed

        time_manager.shift_current_time(timedelta(seconds=(timelock_duration)))
        time_manager.shift_current_timestamp(dual_governance.state.config.tie_break_activation_timeout + Timestamp(1))

        tiebreaker.execute_schedule_proposal(proposal_id)

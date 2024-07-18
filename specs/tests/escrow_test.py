from specs.escrow.escrow import Escrow, EscrowState
from hypothesis import assume, given
from hypothesis import strategies as st
from specs.utils import ether_base

from specs.tests.log import setup_logger

from .utils import sample_stETH_total_supply, test_escrow_address

logger = setup_logger()


@given(st.integers(min_value=0))
def test_stake_stETH(stake):
    escrow = Escrow(MASTER_COPY=test_escrow_address)
    escrow.initialize(test_escrow_address, sample_stETH_total_supply)

    staked = escrow.staked_stETH

    escrow.stake_stETH(stake)
    if stake > 0:
        assert escrow.staked_stETH > staked
    else:
        assert escrow.staked_stETH == staked


@given(st.integers())
def test_finalize_ETH(x):
    escrow = Escrow()
    escrow.initialize(test_escrow_address, sample_stETH_total_supply)

    fETH = escrow.finalized_ETH

    escrow.finalizeETH(x)
    if x > 0:
        assert escrow.finalized_ETH > fETH
    else:
        assert escrow.finalized_ETH == x


@given(st.integers(min_value=1), st.integers(min_value=1))
def test_get_rage_quit_support(stake, finalize):
    assume(stake > finalize)
    escrow = Escrow()
    escrow.initialize(test_escrow_address, sample_stETH_total_supply)

    escrow.stake_stETH(stake)
    escrow.finalizeETH(finalize)

    rage_quit_support = escrow.get_rage_quit_support()

    test_calculation = (ether_base * (escrow.staked_stETH + escrow.finalized_ETH)) / (
        escrow.total_supply + escrow.finalized_ETH
    )

    assert test_calculation == rage_quit_support


@given(st.integers(), st.integers())
def test_start_rage_quit(delay, timelock):
    escrow = Escrow()
    escrow.initialize(test_escrow_address, sample_stETH_total_supply)
    assert escrow.state == EscrowState.SignallingEscrow

    escrow.start_rage_quit(delay, timelock)
    assert escrow.rage_quit_extension_delay == delay
    assert escrow.rage_quit_withdrawals_timelock == timelock
    assert escrow.state == EscrowState.RageQuitEscrow

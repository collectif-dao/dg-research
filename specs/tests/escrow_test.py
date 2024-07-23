from datetime import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.dual_governance.config import DualGovernanceConfig
from specs.dual_governance.state import DualGovernanceState, State
from specs.escrow.escrow import Escrow
from specs.lido import Lido
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.log import setup_logger
from specs.types.shares_value import SharesValue, SharesValueOverflow

from .utils import sample_stETH_total_supply, test_escrow_address

logger = setup_logger()


@given(ethereum_address_strategy(), st.integers(min_value=1))
def test_lock_stETH(holder_addr, lock):
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, sample_stETH_total_supply, datetime.now(), lido=lido)
    escrow: Escrow = dgState.signalling_escrow

    first_threshold = config.first_seal_rage_quit_support
    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares
    rage_quit_support = escrow.get_rage_quit_support()

    if total_locked_shares.value + lock > SharesValue.MAX_VALUE:
        with pytest.raises(SharesValueOverflow):
            escrow.lock_stETH(holder_addr, lock)
    else:
        escrow.lock_stETH(holder_addr, lock)
        assert escrow.accounting.state.stETHTotals.lockedShares > total_locked_shares

        assert escrow.accounting.state.unstETHTotals.finalizedETH.value == 0
        assert escrow.accounting.state.unstETHTotals.unfinalizedShares.value == 0

        rage_quit_support = escrow.get_rage_quit_support()

        if rage_quit_support > first_threshold:
            assert dgState.state == State.VetoSignalling
        else:
            assert dgState.state == State.Normal


# # @given(st.integers())
# # def test_finalize_ETH(x):
# #     escrow = Escrow()
# #     escrow.initialize(test_escrow_address, sample_stETH_total_supply)

# #     fETH = escrow.finalized_ETH

# #     escrow.finalizeETH(x)
# #     if x > 0:
# #         assert escrow.finalized_ETH > fETH
# #     else:
# #         assert escrow.finalized_ETH == x


# # @given(st.integers(min_value=1), st.integers(min_value=1))
# # def test_get_rage_quit_support(stake, finalize):
# #     assume(stake > finalize)
# #     escrow = Escrow()
# #     escrow.initialize(test_escrow_address, sample_stETH_total_supply)

# #     escrow.stake_stETH(stake)
# #     escrow.finalizeETH(finalize)

# #     rage_quit_support = escrow.get_rage_quit_support()

# #     test_calculation = (ether_base * (escrow.staked_stETH + escrow.finalized_ETH)) / (
# #         escrow.total_supply + escrow.finalized_ETH
# #     )

# #     assert test_calculation == rage_quit_support


# # @given(st.integers(), st.integers())
# # def test_start_rage_quit(delay, timelock):
# #     escrow = Escrow()
# #     escrow.initialize(test_escrow_address, sample_stETH_total_supply)
# #     assert escrow.state == EscrowState.SignallingEscrow

# #     escrow.start_rage_quit(delay, timelock)
# #     assert escrow.rage_quit_extension_delay == delay
# #     assert escrow.rage_quit_withdrawals_timelock == timelock
# #     assert escrow.state == EscrowState.RageQuitEscrow

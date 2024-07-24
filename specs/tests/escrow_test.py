from datetime import timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.dual_governance.config import DualGovernanceConfig
from specs.dual_governance.state import DualGovernanceState, State
from specs.escrow.errors import Errors
from specs.escrow.escrow import Escrow, EscrowState
from specs.lido import Lido
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.log import setup_logger
from specs.time_manager import TimeManager
from specs.types.shares_value import SharesValue, SharesValueOverflow
from specs.types.timestamp import Timestamp

from .utils import calc_rage_quit_support, sample_stETH_total_supply, test_escrow_address

logger = setup_logger()


@given(ethereum_address_strategy(), st.integers(min_value=1))
def test_lock_stETH(holder_addr, lock):
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    time_manager = TimeManager()
    time_manager.initialize()
    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
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


@given(ethereum_address_strategy(), st.integers(min_value=1))
def test_unlock_stETH(holder_addr, lock):
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    time_manager = TimeManager()
    time_manager.initialize()
    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
    escrow: Escrow = dgState.signalling_escrow

    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares

    if total_locked_shares.value + lock > SharesValue.MAX_VALUE:
        with pytest.raises(SharesValueOverflow):
            escrow.lock_stETH(holder_addr, lock)
    else:
        escrow.lock_stETH(holder_addr, lock)

        with pytest.raises(Errors.AssetsUnlockDelayNotPassed):
            escrow.unlock_stETH(holder_addr)

        time_manager.shift_current_time(timedelta(hours=6))
        escrow.unlock_stETH(holder_addr)

        assert escrow.accounting.state.stETHTotals.lockedShares == SharesValue(0)


@given(ethereum_address_strategy(), st.integers(min_value=1))
def test_lock_wstETH(holder_addr, lock):
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    time_manager = TimeManager()
    time_manager.initialize()
    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
    escrow: Escrow = dgState.signalling_escrow

    first_threshold = config.first_seal_rage_quit_support
    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares
    rage_quit_support = escrow.get_rage_quit_support()

    if total_locked_shares.value + lock > SharesValue.MAX_VALUE:
        with pytest.raises(SharesValueOverflow):
            escrow.lock_wstETH(holder_addr, lock)
    else:
        escrow.lock_wstETH(holder_addr, lock)
        assert escrow.accounting.state.stETHTotals.lockedShares > total_locked_shares

        rage_quit_support = escrow.get_rage_quit_support()

        if rage_quit_support > first_threshold:
            assert dgState.state == State.VetoSignalling
        else:
            assert dgState.state == State.Normal


@given(ethereum_address_strategy(), st.integers(min_value=1))
def test_unlock_wstETH(holder_addr, lock):
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    time_manager = TimeManager()
    time_manager.initialize()
    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
    escrow: Escrow = dgState.signalling_escrow

    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares

    if total_locked_shares.value + lock > SharesValue.MAX_VALUE:
        with pytest.raises(SharesValueOverflow):
            escrow.lock_wstETH(holder_addr, lock)
    else:
        escrow.lock_wstETH(holder_addr, lock)

        with pytest.raises(Errors.AssetsUnlockDelayNotPassed):
            escrow.unlock_wstETH(holder_addr)

        time_manager.shift_current_time(timedelta(hours=6))
        escrow.unlock_wstETH(holder_addr)

        assert escrow.accounting.state.stETHTotals.lockedShares == SharesValue(0)


@given(ethereum_address_strategy(), st.integers(min_value=1, max_value=SharesValue.MAX_VALUE))
def test_get_rage_quit_support(holder_addr, lock):
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    time_manager = TimeManager()
    time_manager.initialize()
    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
    escrow: Escrow = dgState.signalling_escrow

    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares

    if total_locked_shares.value + lock <= SharesValue.MAX_VALUE:
        escrow.lock_stETH(holder_addr, lock)

        rage_quit_support = escrow.get_rage_quit_support()
        test_calc = calc_rage_quit_support(escrow)

        assert test_calc == rage_quit_support


@given(st.integers(min_value=1, max_value=Timestamp.MAX_VALUE), st.integers(min_value=1, max_value=Timestamp.MAX_VALUE))
def test_start_rage_quit(delay, timelock):
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)
    time_manager = TimeManager()
    time_manager.initialize()
    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
    escrow: Escrow = dgState.signalling_escrow

    assert escrow.state == EscrowState.SignallingEscrow

    escrow.start_rage_quit(delay, timelock)
    assert escrow.rage_quit_extension_delay == Timestamp(delay)
    assert escrow.rage_quit_withdrawals_timelock == Timestamp(timelock)
    assert escrow.state == EscrowState.RageQuitEscrow

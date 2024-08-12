from datetime import timedelta
from typing import Dict

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from specs.dual_governance.config import DualGovernanceConfig
from specs.dual_governance.state import DualGovernanceState, State
from specs.escrow.accounting import UnstETHRecordStatus
from specs.escrow.errors import Errors
from specs.escrow.escrow import Escrow, EscrowState
from specs.lido import Lido
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.emergency_protection_test import limited_time_strategy
from specs.tests.log import setup_logger
from specs.tests.withdrawals.withdrawal_queue_claims_test import base_share_rate
from specs.tests.withdrawals.withdrawal_queue_request_withdrawals_test import withdrawal_amounts_strategy
from specs.time_manager import TimeManager
from specs.types.address import Address
from specs.types.shares_value import SharesValue, SharesValueOverflow
from specs.types.timestamp import Timestamp
from specs.withdrawals.errors import Errors as WithdrawalErrors

from .utils import calc_rage_quit_support, sample_stETH_total_supply, test_escrow_address

logger = setup_logger()


@given(ethereum_address_strategy(), st.integers(min_value=1))
def test_lock_stETH(holder_addr, lock):
    assume(holder_addr != Address.ZERO)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
    escrow: Escrow = dgState.signalling_escrow

    first_threshold = config.first_seal_rage_quit_support
    total_holder_locked_shares: Dict[str, SharesValue] = {}
    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares
    rage_quit_support = escrow.get_rage_quit_support()

    buffered_ether = lido.get_buffered_ether()
    lido._mint_shares(holder_addr, lock)
    lido.set_buffered_ether(buffered_ether + lock)
    lido.approve(holder_addr, test_escrow_address, lock)

    if holder_addr not in total_holder_locked_shares:
        if holder_addr not in escrow.accounting.state.assets:
            total_holder_locked_shares[holder_addr] = SharesValue.from_uint256(0)
        else:
            total_holder_locked_shares[holder_addr] = escrow.accounting.state.assets[holder_addr].stETHLockedShares

    if total_locked_shares.value + lock > SharesValue.MAX_VALUE:
        with pytest.raises(SharesValueOverflow):
            escrow.lock_stETH(holder_addr, lock)
    else:
        escrow.lock_stETH(holder_addr, lock)
        total_holder_locked_shares[holder_addr] += SharesValue.from_uint256(lock)

        assert lido.balance_of(test_escrow_address) == lock
        assert lido.balance_of(holder_addr) == 0

        assert escrow.accounting.state.stETHTotals.lockedShares > total_locked_shares
        assert escrow.accounting.state.assets[holder_addr].stETHLockedShares == total_holder_locked_shares[holder_addr]

        assert escrow.accounting.state.unstETHTotals.finalizedETH.value == 0
        assert escrow.accounting.state.unstETHTotals.unfinalizedShares.value == 0

        rage_quit_support = escrow.get_rage_quit_support()

        if rage_quit_support > first_threshold:
            assert dgState.state == State.VetoSignalling
        else:
            assert dgState.state == State.Normal


@given(ethereum_address_strategy(), st.integers(min_value=1))
def test_unlock_stETH(holder_addr, lock):
    assume(holder_addr != Address.ZERO)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
    escrow: Escrow = dgState.signalling_escrow
    total_holder_locked_shares: Dict[str, SharesValue] = {}

    if holder_addr not in total_holder_locked_shares:
        if holder_addr not in escrow.accounting.state.assets:
            total_holder_locked_shares[holder_addr] = SharesValue.from_uint256(0)
        else:
            total_holder_locked_shares[holder_addr] = escrow.accounting.state.assets[holder_addr].stETHLockedShares

    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares

    buffered_ether = lido.get_buffered_ether()
    lido._mint_shares(holder_addr, lock)
    lido.set_buffered_ether(buffered_ether + lock)
    lido.approve(holder_addr, test_escrow_address, lock)

    if total_locked_shares.value + lock > SharesValue.MAX_VALUE:
        with pytest.raises(SharesValueOverflow):
            escrow.lock_stETH(holder_addr, lock)
    else:
        escrow.lock_stETH(holder_addr, lock)
        total_holder_locked_shares[holder_addr] += SharesValue.from_uint256(lock)

        with pytest.raises(Errors.AssetsUnlockDelayNotPassed):
            escrow.unlock_stETH(holder_addr)

        time_manager.shift_current_time(timedelta(hours=6))
        escrow.unlock_stETH(holder_addr)
        total_holder_locked_shares[holder_addr] -= SharesValue.from_uint256(lock)

        assert escrow.accounting.state.assets[holder_addr].stETHLockedShares == total_holder_locked_shares[holder_addr]
        assert escrow.accounting.state.stETHTotals.lockedShares == SharesValue(0)

        assert lido.balance_of(test_escrow_address) == 0
        assert lido.balance_of(holder_addr) == lock


@given(ethereum_address_strategy(), st.integers(min_value=1))
def test_lock_wstETH(holder_addr, lock):
    assume(holder_addr != Address.ZERO)
    time_manager = TimeManager()
    time_manager.initialize()
    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)
    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
    escrow: Escrow = dgState.signalling_escrow

    first_threshold = config.first_seal_rage_quit_support
    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares
    rage_quit_support = escrow.get_rage_quit_support()

    buffered_ether = lido.get_buffered_ether()
    lido._mint_shares(holder_addr, lock)
    lido.set_buffered_ether(buffered_ether + lock)
    lido.approve(holder_addr, Address.wstETH, lock)
    lido.wrap(holder_addr, lock)
    lido.wstETH.approve(holder_addr, test_escrow_address, lock)

    if total_locked_shares.value + lock > SharesValue.MAX_VALUE:
        with pytest.raises(SharesValueOverflow):
            escrow.lock_wstETH(holder_addr, lock)
    else:
        escrow.lock_wstETH(holder_addr, lock)
        assert escrow.accounting.state.stETHTotals.lockedShares > total_locked_shares

        assert lido.balance_of(test_escrow_address) == lock
        assert lido.balance_of(holder_addr) == 0
        assert lido.wstETH.balance_of(test_escrow_address) == 0
        assert lido.wstETH.balance_of(holder_addr) == 0

        rage_quit_support = escrow.get_rage_quit_support()

        if rage_quit_support > first_threshold:
            assert dgState.state == State.VetoSignalling
        else:
            assert dgState.state == State.Normal


@given(ethereum_address_strategy(), st.integers(min_value=1))
def test_unlock_wstETH(holder_addr, lock):
    assume(holder_addr != Address.ZERO)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido)
    escrow: Escrow = dgState.signalling_escrow

    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares

    buffered_ether = lido.get_buffered_ether()
    lido._mint_shares(holder_addr, lock)
    lido.set_buffered_ether(buffered_ether + lock)
    lido.approve(holder_addr, Address.wstETH, lock)
    lido.wrap(holder_addr, lock)
    lido.wstETH.approve(holder_addr, test_escrow_address, lock)

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

        assert lido.wstETH.balance_of(holder_addr) == lock
        assert lido.wstETH.balance_of(test_escrow_address) == 0


@given(ethereum_address_strategy(), st.integers(min_value=1, max_value=SharesValue.MAX_VALUE))
def test_get_rage_quit_support(holder_addr, lock):
    assume(holder_addr != Address.ZERO)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido)
    escrow: Escrow = dgState.signalling_escrow

    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares

    buffered_ether = lido.get_buffered_ether()
    lido._mint_shares(holder_addr, lock)
    lido.set_buffered_ether(buffered_ether + lock)
    lido.approve(holder_addr, test_escrow_address, lock)

    if total_locked_shares.value + lock <= SharesValue.MAX_VALUE:
        escrow.lock_stETH(holder_addr, lock)

        rage_quit_support = escrow.get_rage_quit_support()
        test_calc = calc_rage_quit_support(escrow)

        assert test_calc == rage_quit_support


@given(st.integers(min_value=1, max_value=Timestamp.MAX_VALUE), st.integers(min_value=1, max_value=Timestamp.MAX_VALUE))
def test_start_rage_quit(delay, timelock):
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido)
    escrow: Escrow = dgState.signalling_escrow

    assert escrow.state == EscrowState.SignallingEscrow

    delay_timestamp = Timestamp(delay)
    timelock_timestamp = Timestamp(timelock)

    escrow.start_rage_quit(delay_timestamp, timelock_timestamp)
    assert escrow.rage_quit_extension_delay == delay_timestamp
    assert escrow.rage_quit_withdrawals_timelock == timelock_timestamp
    assert escrow.state == EscrowState.RageQuitEscrow


@given(
    ethereum_address_strategy(),
    withdrawal_amounts_strategy(100, 1000 * 10**18),
)
def test_unstETH_flows(holder_addr, withdrawal_amounts):
    assume(holder_addr != Address.ZERO)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
    escrow: Escrow = dgState.signalling_escrow

    first_threshold = config.first_seal_rage_quit_support
    total_holder_unstETH_locked: Dict[str, SharesValue] = {}
    total_locked_unstETH = escrow.accounting.state.unstETHTotals.unfinalizedShares
    rage_quit_support = escrow.get_rage_quit_support()

    total_stETH_amount: int = 0
    for amount in withdrawal_amounts:
        total_stETH_amount += amount

    buffered_ether = lido.get_buffered_ether()
    lido._mint_shares(holder_addr, total_stETH_amount)
    lido.set_buffered_ether(buffered_ether + total_stETH_amount)
    lido.approve(holder_addr, test_escrow_address, total_stETH_amount)
    lido.approve(holder_addr, Address.withdrawal_queue, total_stETH_amount)

    if holder_addr not in total_holder_unstETH_locked:
        if holder_addr not in escrow.accounting.state.assets:
            total_holder_unstETH_locked[holder_addr] = SharesValue.from_uint256(0)
        else:
            total_holder_unstETH_locked[holder_addr] = escrow.accounting.state.assets[holder_addr].unstETHLockedShares

    request_ids = escrow.withdrawal_queue.request_withdrawals(holder_addr, withdrawal_amounts)

    escrow.lock_unstETH(holder_addr, request_ids)
    total_holder_unstETH_locked[holder_addr] += SharesValue.from_uint256(total_stETH_amount)

    assert escrow.withdrawal_queue.balanceOf(holder_addr) == 0
    assert escrow.withdrawal_queue.balanceOf(test_escrow_address) == len(request_ids)

    assert lido.balance_of(Address.withdrawal_queue) == total_stETH_amount
    assert lido.balance_of(holder_addr) == 0

    assert escrow.accounting.state.unstETHTotals.unfinalizedShares > total_locked_unstETH
    assert escrow.accounting.state.assets[holder_addr].unstETHLockedShares == total_holder_unstETH_locked[holder_addr]

    rage_quit_support = escrow.get_rage_quit_support()

    if rage_quit_support > first_threshold:
        assert dgState.state == State.VetoSignalling
    else:
        assert dgState.state == State.Normal

    time_manager.shift_current_time(timedelta(hours=6))
    escrow.unlock_unstETH(holder_addr, request_ids)
    total_holder_unstETH_locked[holder_addr] -= SharesValue.from_uint256(total_stETH_amount)

    assert escrow.withdrawal_queue.balanceOf(test_escrow_address) == 0
    assert escrow.withdrawal_queue.balanceOf(holder_addr) == len(request_ids)

    assert lido.balance_of(Address.withdrawal_queue) == total_stETH_amount
    assert lido.balance_of(holder_addr) == 0

    assert escrow.accounting.state.unstETHTotals.unfinalizedShares.value == 0
    assert escrow.accounting.state.assets[holder_addr].unstETHLockedShares == total_holder_unstETH_locked[holder_addr]

    escrow.lock_unstETH(holder_addr, request_ids)
    total_holder_unstETH_locked[holder_addr] += SharesValue.from_uint256(total_stETH_amount)
    escrow.withdrawal_queue.finalize(request_ids[-1], total_stETH_amount, base_share_rate)

    hints = escrow.withdrawal_queue.find_checkpoint_hints(
        request_ids, 1, escrow.withdrawal_queue.get_last_checkpoint_index()
    )

    assert escrow.accounting.state.unstETHTotals.unfinalizedShares > total_locked_unstETH
    assert escrow.accounting.state.assets[holder_addr].unstETHLockedShares == total_holder_unstETH_locked[holder_addr]

    escrow.mark_unstETH_finalized(request_ids, hints)

    for i, request_id in enumerate(request_ids):
        assert escrow.accounting.state.unstETHRecords[request_id].lockedBy == holder_addr
        assert escrow.accounting.state.unstETHRecords[request_id].status == UnstETHRecordStatus.Finalized
        assert escrow.accounting.state.unstETHRecords[request_id].shares.value == withdrawal_amounts[i]
        assert escrow.accounting.state.unstETHRecords[request_id].claimableAmount.value == withdrawal_amounts[i]


@given(ethereum_address_strategy(), st.integers(min_value=1))
def test_lock_stETH_and_request_withdrawals(holder_addr, lock):
    assume(holder_addr != Address.ZERO)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
    escrow: Escrow = dgState.signalling_escrow

    total_locked_shares = escrow.accounting.state.stETHTotals.lockedShares

    buffered_ether = lido.get_buffered_ether()
    lido._mint_shares(holder_addr, lock)
    lido.set_buffered_ether(buffered_ether + lock)
    lido.approve(holder_addr, test_escrow_address, lock)

    if total_locked_shares.value + lock > SharesValue.MAX_VALUE:
        with pytest.raises(SharesValueOverflow):
            escrow.lock_stETH(holder_addr, lock)
    else:
        escrow.lock_stETH(holder_addr, lock)

        assert lido.balance_of(test_escrow_address) == lock
        assert lido.balance_of(holder_addr) == 0

        if lock < escrow.withdrawal_queue.MIN_STETH_WITHDRAWAL_AMOUNT:
            with pytest.raises(WithdrawalErrors.RequestAmountTooSmall):
                escrow.request_withdrawals(holder_addr, [lock])
        elif lock > escrow.withdrawal_queue.MAX_STETH_WITHDRAWAL_AMOUNT:
            with pytest.raises(WithdrawalErrors.RequestAmountTooLarge):
                escrow.request_withdrawals(holder_addr, [lock])

        else:
            escrow.request_withdrawals(holder_addr, [lock])

            assert lido.balance_of(test_escrow_address) == 0
            assert lido.balance_of(Address.withdrawal_queue) == lock

            assert escrow.withdrawal_queue.balanceOf(test_escrow_address) == 1


@given(
    ethereum_address_strategy(),
    withdrawal_amounts_strategy(100, 1000 * 10**18, 8),
    limited_time_strategy(),
    limited_time_strategy(),
)
def test_full_stETH_to_unstETH_to_withdraw_ETH_flow(holder_addr, withdrawal_amounts, delay, timelock):
    assume(holder_addr != Address.ZERO)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
    escrow: Escrow = dgState.signalling_escrow

    delay_timestamp = Timestamp(delay)
    timelock_timestamp = Timestamp(timelock)

    total_stETH_amount: int = 0
    for amount in withdrawal_amounts:
        total_stETH_amount += amount

    buffered_ether = lido.get_buffered_ether()
    lido._mint_shares(holder_addr, total_stETH_amount)
    lido.set_buffered_ether(buffered_ether + total_stETH_amount)
    lido.approve(holder_addr, test_escrow_address, total_stETH_amount)

    escrow.lock_stETH(holder_addr, total_stETH_amount)

    escrow.start_rage_quit(delay_timestamp, timelock_timestamp)

    requested_amounts = escrow.batches_queue.calc_request_amounts(
        escrow.min_withdrawal_request_amount,
        escrow.max_withdrawal_request_amount,
        min(lido.balance_of(test_escrow_address), (escrow.max_withdrawal_request_amount * len(withdrawal_amounts))),
    )

    escrow.request_next_withdrawals_batch(len(withdrawal_amounts))

    assert escrow.withdrawal_queue.balanceOf(test_escrow_address) == len(requested_amounts)

    unstETH_ids = escrow.withdrawal_queue.get_withdrawal_requests(test_escrow_address)

    escrow.withdrawal_queue.finalize(unstETH_ids[-1], total_stETH_amount, 1 * 10**27)

    escrow.claim_next_withdrawals_batch(len(unstETH_ids))
    escrow.start_rage_quit_extension_delay()

    time_manager.shift_current_timestamp(delay_timestamp + timelock_timestamp + Timestamp(1))

    eth_to_withdraw = escrow.withdraw_ETH(holder_addr)
    assert eth_to_withdraw.value == total_stETH_amount


@given(
    ethereum_address_strategy(),
    withdrawal_amounts_strategy(100, 1000 * 10**18, 8),
    limited_time_strategy(),
    limited_time_strategy(),
)
def test_lock_unstETH_to_withdraw_from_unstETH_flow(holder_addr, withdrawal_amounts, delay, timelock):
    assume(holder_addr != Address.ZERO)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    config = DualGovernanceConfig()
    dgState = DualGovernanceState(config)
    dgState.initialize(test_escrow_address, time_manager, lido=lido)
    escrow: Escrow = dgState.signalling_escrow

    delay_timestamp = Timestamp(delay)
    timelock_timestamp = Timestamp(timelock)

    total_stETH_amount: int = 0
    for amount in withdrawal_amounts:
        total_stETH_amount += amount

    buffered_ether = lido.get_buffered_ether()
    lido._mint_shares(holder_addr, total_stETH_amount)
    lido.set_buffered_ether(buffered_ether + total_stETH_amount)
    lido.approve(holder_addr, test_escrow_address, total_stETH_amount)
    lido.approve(holder_addr, Address.withdrawal_queue, total_stETH_amount)

    request_ids = escrow.withdrawal_queue.request_withdrawals(holder_addr, withdrawal_amounts)

    escrow.lock_unstETH(holder_addr, request_ids)

    escrow.start_rage_quit(delay_timestamp, timelock_timestamp)

    assert escrow.withdrawal_queue.balanceOf(test_escrow_address) == len(withdrawal_amounts)

    escrow.withdrawal_queue.finalize(request_ids[-1], total_stETH_amount, 1 * 10**27)

    hints = escrow.withdrawal_queue.find_checkpoint_hints(
        request_ids, 1, escrow.withdrawal_queue.get_last_checkpoint_index()
    )

    escrow.claim_unstETH(request_ids, hints)
    escrow.start_rage_quit_extension_delay()

    time_manager.shift_current_timestamp(delay_timestamp + timelock_timestamp + Timestamp(1))

    eth_to_withdraw = escrow.withdraw_eth_from_unstETH_ids(holder_addr, request_ids)
    assert eth_to_withdraw.value == total_stETH_amount

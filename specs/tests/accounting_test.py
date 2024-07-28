from typing import Dict, List

import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.escrow.accounting import (
    AssetsAccounting,
    UnstETHRecordStatus,
    WithdrawalRequestStatus,
)
from specs.escrow.errors import Errors
from specs.time_manager import TimeManager
from specs.types.eth_value import ETHValue, ETHValueOverflow
from specs.types.shares_value import SharesValue, SharesValueOverflow


def ethereum_address_strategy():
    return st.binary(min_size=20, max_size=20).map(lambda x: "0x" + x.hex())


def base_int_strategy():
    return st.integers(min_value=1, max_value=SharesValue.MAX_VALUE)


def withdrawal_request_status_strategy():
    return st.lists(
        st.builds(
            WithdrawalRequestStatus,
            amount_of_stETH=st.integers(min_value=1, max_value=10000),
            amount_of_shares=st.integers(min_value=1, max_value=10000),
            owner=ethereum_address_strategy(),
            timestamp=st.integers(min_value=1, max_value=2**256 - 1),
        ),
        min_size=1,
    )


def unstETHids_strategy():
    return st.lists(st.integers(min_value=0, max_value=1000), unique=True)


def generate_unstETH_lists():
    return st.tuples(unstETHids_strategy(), withdrawal_request_status_strategy()).map(
        lambda t: (t[0][: len(t[0])], t[1][: len(t[0])])
    )


@given(holder=ethereum_address_strategy(), shares=base_int_strategy())
def test_accountStETHSharesLock(holder, shares):
    time_manager = TimeManager()
    time_manager.initialize()
    accounting = AssetsAccounting()
    accounting.initialize(time_manager)

    total_locked_shares: SharesValue = accounting.state.stETHTotals.lockedShares
    total_holder_locked_shares: Dict[str, SharesValue] = {}
    shares_value = SharesValue(shares)

    if holder not in total_holder_locked_shares:
        if holder not in accounting.state.assets:
            total_holder_locked_shares[holder] = SharesValue.from_uint256(0)
        else:
            total_holder_locked_shares[holder] = accounting.state.assets[holder].stETHLockedShares

    if total_locked_shares.value + shares > SharesValue.MAX_VALUE:
        with pytest.raises(SharesValueOverflow):
            accounting.accountStETHSharesLock(holder, shares_value)
    else:
        accounting.accountStETHSharesLock(holder, shares_value)

        total_holder_locked_shares[holder] += shares_value
        total_locked_shares += shares_value

        assert holder in accounting.state.assets
        assert accounting.state.assets[holder].stETHLockedShares == total_holder_locked_shares[holder]
        assert accounting.state.stETHTotals.lockedShares == total_locked_shares


@given(holder=ethereum_address_strategy(), lock=base_int_strategy(), unlock=base_int_strategy())
def test_accountStETHSharesUnlock(holder, lock, unlock):
    time_manager = TimeManager()
    time_manager.initialize()
    accounting = AssetsAccounting()
    accounting.initialize(time_manager)

    total_locked_shares: SharesValue = accounting.state.stETHTotals.lockedShares
    total_holder_locked_shares: Dict[str, SharesValue] = {}
    lock_shares = SharesValue(lock)
    unlock_shares = SharesValue(unlock)

    if holder not in total_holder_locked_shares:
        if holder not in accounting.state.assets:
            total_holder_locked_shares[holder] = SharesValue.from_uint256(0)
        else:
            total_holder_locked_shares[holder] = accounting.state.assets[holder].stETHLockedShares

    if total_locked_shares.value + lock > SharesValue.MAX_VALUE:
        with pytest.raises(SharesValueOverflow):
            accounting.accountStETHSharesLock(holder, lock_shares)
    else:
        accounting.accountStETHSharesLock(holder, lock_shares)

        if accounting.state.assets[holder].stETHLockedShares < unlock_shares:
            with pytest.raises(Errors.InvalidSharesValue):
                accounting.accountStETHSharesUnlock(holder, unlock_shares)
        else:
            accounting.accountStETHSharesUnlock(holder, unlock_shares)

            total_holder_locked_shares[holder] += lock_shares - unlock_shares
            total_locked_shares += lock_shares - unlock_shares

            assert holder in accounting.state.assets
            assert accounting.state.assets[holder].stETHLockedShares == total_holder_locked_shares[holder]
            assert accounting.state.stETHTotals.lockedShares == total_locked_shares


@given(holder=ethereum_address_strategy(), lock=base_int_strategy())
def test_accountStETHSharesWithdraw(holder, lock):
    time_manager = TimeManager()
    time_manager.initialize()
    accounting = AssetsAccounting()
    accounting.initialize(time_manager)

    total_locked_shares: SharesValue = accounting.state.stETHTotals.lockedShares
    total_holder_locked_shares: Dict[str, SharesValue] = {}
    lock_shares = SharesValue(lock)

    if holder not in total_holder_locked_shares:
        if holder not in accounting.state.assets:
            total_holder_locked_shares[holder] = SharesValue.from_uint256(0)
        else:
            total_holder_locked_shares[holder] = accounting.state.assets[holder].stETHLockedShares

    if total_locked_shares.value + lock > SharesValue.MAX_VALUE:
        with pytest.raises(SharesValueOverflow):
            accounting.accountStETHSharesLock(holder, lock_shares)
    else:
        accounting.accountStETHSharesLock(holder, lock_shares)

        target_withdrawn = SharesValue.calc_eth_value(
            accounting.state.stETHTotals.claimedETH,
            accounting.state.assets[holder].stETHLockedShares,
            accounting.state.stETHTotals.lockedShares,
        )

        withdrawn: ETHValue = accounting.accountStETHSharesWithdraw(holder)

        assert holder in accounting.state.assets
        assert target_withdrawn == withdrawn
        assert accounting.state.assets[holder].stETHLockedShares == SharesValue.from_uint256(0)


@given(claim=base_int_strategy())
def test_accountClaimedStETH(claim):
    time_manager = TimeManager()
    time_manager.initialize()
    accounting = AssetsAccounting()
    accounting.initialize(time_manager)
    total_claimed_eth: SharesValue = accounting.state.stETHTotals.claimedETH
    claim_value = ETHValue(claim)

    if total_claimed_eth.value + claim > SharesValue.MAX_VALUE:
        with pytest.raises(ETHValueOverflow):
            accounting.accountClaimedStETH(claim_value)
    else:
        accounting.accountClaimedStETH(claim_value)
        total_claimed_eth += claim_value

        assert accounting.state.stETHTotals.claimedETH == total_claimed_eth


@given(holder=ethereum_address_strategy(), params=generate_unstETH_lists())
def test_accountUnstETHLock(holder, params):
    repeated_ids: bool = False
    time_manager = TimeManager()
    time_manager.initialize()
    accounting = AssetsAccounting()
    accounting.initialize(time_manager)
    unstETHids: List[int] = params[0]
    withdrawal_requests: List[WithdrawalRequestStatus] = params[1]
    total_shares: SharesValue = SharesValue(0)

    for req in withdrawal_requests:
        total_shares += SharesValue(req.amount_of_shares)

    total_unfinalized_shares: SharesValue = accounting.state.unstETHTotals.unfinalizedShares
    total_holder_locked_shares: Dict[str, SharesValue] = {}

    if holder not in total_holder_locked_shares:
        if holder not in accounting.state.assets:
            total_holder_locked_shares[holder] = SharesValue.from_uint256(0)
        else:
            total_holder_locked_shares[holder] = accounting.state.assets[holder].unstETHLockedShares

    for id in unstETHids:
        if (
            id in accounting.state.unstETHRecords
            and accounting.state.unstETHRecords[id].status == UnstETHRecordStatus.Locked
        ):
            repeated_ids = True

    withdrawal_requests: List[WithdrawalRequestStatus] = params[1]

    if len(unstETHids) != len(withdrawal_requests):
        with pytest.raises(Errors.IncorrectParameters):
            accounting.accountUnstETHLock(holder, unstETHids, withdrawal_requests)
    else:
        if repeated_ids:
            with pytest.raises(Errors.InvalidUnstETHStatus):
                accounting.accountUnstETHLock(holder, unstETHids, withdrawal_requests)
        else:
            accounting.accountUnstETHLock(holder, unstETHids, withdrawal_requests)
            total_unfinalized_shares += total_shares
            total_holder_locked_shares[holder] += total_shares

            assert accounting.state.assets[holder].unstETHLockedShares == total_holder_locked_shares[holder]
            assert accounting.state.unstETHTotals.unfinalizedShares == total_unfinalized_shares


@given(holder=ethereum_address_strategy(), params=generate_unstETH_lists())
def test_accountUnstETHUnlock(holder, params):
    repeated_ids: bool = False
    time_manager = TimeManager()
    time_manager.initialize()
    accounting = AssetsAccounting()
    accounting.initialize(time_manager)
    unstETHids: List[int] = params[0]
    withdrawal_requests: List[WithdrawalRequestStatus] = params[1]
    total_shares: SharesValue = SharesValue(0)
    claimable_amounts: List[int] = []

    for req in withdrawal_requests:
        total_shares += SharesValue(req.amount_of_shares)
        claimable_amounts.append(req.amount_of_shares)

    total_unfinalized_shares: SharesValue = accounting.state.unstETHTotals.unfinalizedShares
    total_holder_locked_shares: Dict[str, SharesValue] = {}

    if holder not in total_holder_locked_shares:
        if holder not in accounting.state.assets:
            total_holder_locked_shares[holder] = SharesValue.from_uint256(0)
        else:
            total_holder_locked_shares[holder] = accounting.state.assets[holder].unstETHLockedShares

    for id in unstETHids:
        if (
            id in accounting.state.unstETHRecords
            and accounting.state.unstETHRecords[id].status != UnstETHRecordStatus.NotLocked
        ):
            repeated_ids = True

    withdrawal_requests: List[WithdrawalRequestStatus] = params[1]

    if len(unstETHids) != len(withdrawal_requests):
        with pytest.raises(Errors.IncorrectParameters):
            accounting.accountUnstETHLock(holder, unstETHids, withdrawal_requests)
    else:
        if repeated_ids:
            with pytest.raises(Errors.InvalidUnstETHStatus):
                accounting.accountUnstETHLock(holder, unstETHids, withdrawal_requests)
        else:
            accounting.accountUnstETHLock(holder, unstETHids, withdrawal_requests)

            total_unfinalized_shares: SharesValue = accounting.state.unstETHTotals.unfinalizedShares
            total_finalized_eth: ETHValue = accounting.state.unstETHTotals.finalizedETH

            accounting.accountUnstETHFinalized(unstETHids, claimable_amounts)
            accounting.accountUnstETHUnlock(holder, unstETHids)

            total_holder_locked_shares[holder] = (
                total_holder_locked_shares[holder] - total_shares
                if total_holder_locked_shares[holder] > total_shares
                else SharesValue.from_uint256(0)
            )
            total_finalized_eth = (
                total_finalized_eth - ETHValue.from_uint256(total_shares.value)
                if total_finalized_eth.value > total_shares.value
                else ETHValue.from_uint256(0)
            )
            total_unfinalized_shares = (
                total_unfinalized_shares - total_shares
                if total_unfinalized_shares > total_shares
                else SharesValue.from_uint256(0)
            )

            assert accounting.state.unstETHTotals.finalizedETH == total_finalized_eth
            assert accounting.state.assets[holder].unstETHLockedShares == total_holder_locked_shares[holder]
            assert accounting.state.unstETHTotals.unfinalizedShares == total_unfinalized_shares


@given(holder=ethereum_address_strategy(), params=generate_unstETH_lists())
def test_accountUnstETHFinalized(holder, params):
    repeated_ids: bool = False
    time_manager = TimeManager()
    time_manager.initialize()
    accounting = AssetsAccounting()
    accounting.initialize(time_manager)
    unstETHids: List[int] = params[0]
    withdrawal_requests: List[WithdrawalRequestStatus] = params[1]
    total_shares: SharesValue = SharesValue(0)
    claimable_amounts: List[int] = []
    total_finalized_amount: int = 0

    for req in withdrawal_requests:
        total_shares += SharesValue(req.amount_of_shares)
        claimable_amounts.append(req.amount_of_shares)
        total_finalized_amount += req.amount_of_shares

    total_holder_locked_shares: Dict[str, SharesValue] = {}

    if holder not in total_holder_locked_shares:
        if holder not in accounting.state.assets:
            total_holder_locked_shares[holder] = SharesValue.from_uint256(0)
        else:
            total_holder_locked_shares[holder] = accounting.state.assets[holder].unstETHLockedShares

    for id in unstETHids:
        if (
            id in accounting.state.unstETHRecords
            and accounting.state.unstETHRecords[id].status != UnstETHRecordStatus.NotLocked
        ):
            repeated_ids = True

    withdrawal_requests: List[WithdrawalRequestStatus] = params[1]

    if len(unstETHids) != len(withdrawal_requests):
        with pytest.raises(Errors.IncorrectParameters):
            accounting.accountUnstETHFinalized(unstETHids, claimable_amounts)
    else:
        if repeated_ids:
            with pytest.raises(Errors.InvalidUnstETHStatus):
                accounting.accountUnstETHLock(holder, unstETHids, withdrawal_requests)
        else:
            accounting.accountUnstETHLock(holder, unstETHids, withdrawal_requests)

            total_unfinalized_shares: SharesValue = accounting.state.unstETHTotals.unfinalizedShares
            total_finalized_eth: ETHValue = accounting.state.unstETHTotals.finalizedETH

            accounting.accountUnstETHFinalized(unstETHids, claimable_amounts)

            total_finalized_eth += ETHValue.from_uint256(total_finalized_amount)
            total_unfinalized_shares -= SharesValue.from_uint256(total_finalized_amount)

            assert accounting.state.unstETHTotals.finalizedETH == total_finalized_eth
            assert accounting.state.unstETHTotals.unfinalizedShares == total_unfinalized_shares

            for i in range(len(unstETHids)):
                id = unstETHids[i]
                assert accounting.state.unstETHRecords[id].status == UnstETHRecordStatus.Finalized
                assert accounting.state.unstETHRecords[id].claimableAmount.value == claimable_amounts[i]


@given(holder=ethereum_address_strategy(), params=generate_unstETH_lists())
def test_accountUnstETHClaimed(holder, params):
    repeated_ids: bool = False
    time_manager = TimeManager()
    time_manager.initialize()
    accounting = AssetsAccounting()
    accounting.initialize(time_manager)
    unstETHids: List[int] = params[0]
    withdrawal_requests: List[WithdrawalRequestStatus] = params[1]
    total_shares: SharesValue = SharesValue(0)
    claimable_amounts: List[int] = []
    total_claimable_amount: int = 0

    for req in withdrawal_requests:
        total_shares += SharesValue(req.amount_of_shares)
        claimable_amounts.append(req.amount_of_shares)
        total_claimable_amount += req.amount_of_shares

    total_holder_locked_shares: Dict[str, SharesValue] = {}

    if holder not in total_holder_locked_shares:
        if holder not in accounting.state.assets:
            total_holder_locked_shares[holder] = SharesValue.from_uint256(0)
        else:
            total_holder_locked_shares[holder] = accounting.state.assets[holder].unstETHLockedShares

    for id in unstETHids:
        if (
            id in accounting.state.unstETHRecords
            and accounting.state.unstETHRecords[id].status != UnstETHRecordStatus.NotLocked
        ):
            repeated_ids = True

    withdrawal_requests: List[WithdrawalRequestStatus] = params[1]

    if len(unstETHids) != len(withdrawal_requests):
        with pytest.raises(Errors.IncorrectParameters):
            accounting.accountUnstETHClaimed(unstETHids, claimable_amounts)
    else:
        if repeated_ids:
            with pytest.raises(Errors.InvalidUnstETHStatus):
                accounting.accountUnstETHLock(holder, unstETHids, withdrawal_requests)
        else:
            accounting.accountUnstETHLock(holder, unstETHids, withdrawal_requests)
            amount_claimed = accounting.accountUnstETHClaimed(unstETHids, claimable_amounts)

            assert amount_claimed.value == total_claimable_amount

            for i in range(len(unstETHids)):
                id = unstETHids[i]
                assert accounting.state.unstETHRecords[id].status == UnstETHRecordStatus.Claimed
                assert accounting.state.unstETHRecords[id].claimableAmount.value == claimable_amounts[i]


@given(holder=ethereum_address_strategy(), params=generate_unstETH_lists())
def test_accountUnstETHWithdraw(holder, params):
    repeated_ids: bool = False
    time_manager = TimeManager()
    time_manager.initialize()
    accounting = AssetsAccounting()
    accounting.initialize(time_manager)
    unstETHids: List[int] = params[0]
    withdrawal_requests: List[WithdrawalRequestStatus] = params[1]
    total_shares: SharesValue = SharesValue(0)
    claimable_amounts: List[int] = []
    total_withdrawn_amount: int = 0

    for req in withdrawal_requests:
        total_shares += SharesValue(req.amount_of_shares)
        claimable_amounts.append(req.amount_of_shares)
        total_withdrawn_amount += req.amount_of_shares

    total_holder_locked_shares: Dict[str, SharesValue] = {}

    if holder not in total_holder_locked_shares:
        if holder not in accounting.state.assets:
            total_holder_locked_shares[holder] = SharesValue.from_uint256(0)
        else:
            total_holder_locked_shares[holder] = accounting.state.assets[holder].unstETHLockedShares

    for id in unstETHids:
        if (
            id in accounting.state.unstETHRecords
            and accounting.state.unstETHRecords[id].status != UnstETHRecordStatus.NotLocked
        ):
            repeated_ids = True

    withdrawal_requests: List[WithdrawalRequestStatus] = params[1]

    if len(unstETHids) != len(withdrawal_requests):
        with pytest.raises(Errors.IncorrectParameters):
            accounting.accountUnstETHClaimed(unstETHids, claimable_amounts)
    else:
        if repeated_ids:
            with pytest.raises(Errors.InvalidUnstETHStatus):
                accounting.accountUnstETHLock(holder, unstETHids, withdrawal_requests)
        else:
            accounting.accountUnstETHLock(holder, unstETHids, withdrawal_requests)
            amount_claimed = accounting.accountUnstETHClaimed(unstETHids, claimable_amounts)
            amount_withdrawn = accounting.accountUnstETHWithdraw(holder, unstETHids)

            assert amount_withdrawn.value == total_withdrawn_amount
            assert amount_withdrawn == amount_claimed

            for i in range(len(unstETHids)):
                id = unstETHids[i]
                assert accounting.state.unstETHRecords[id].status == UnstETHRecordStatus.Withdrawn
                assert accounting.state.unstETHRecords[id].claimableAmount.value == claimable_amounts[i]

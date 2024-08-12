from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import List

from specs.escrow.accounting import AssetsAccounting
from specs.escrow.withdrawal_batches import WithdrawalsBatchesQueue
from specs.lido import Lido
from specs.time_manager import TimeManager
from specs.types.address import Address
from specs.types.eth_value import ETHValue
from specs.types.shares_value import SharesValue
from specs.types.timestamp import Timestamp, Timestamps
from specs.utils import default, ether_base
from specs.withdrawals.nft import WithdrawalQueueERC721 as WithdrawalQueue

from .errors import Errors


class EscrowState(Enum):
    NotInitialized = 1
    SignallingEscrow = 2
    RageQuitEscrow = 3


@dataclass
class LockedAssetsTotal:
    stETH_locked_shares: int
    stETH_claimed_ETH: int
    unstETH_unfinalized_shares: int
    unstETH_finalized_ETH: int


@dataclass
class VetoerState:
    stETH_locked_shares: int
    unstETH_locked_shares: int
    unstETH_ids_count: int
    last_assets_lock_timestamp: int


@dataclass
class Escrow:
    address: str = field(default_factory=lambda: "")
    state: EscrowState = EscrowState.NotInitialized

    rage_quit_extension_delay: Timestamp = field(default_factory=lambda: Timestamps.ZERO)
    rage_quit_withdrawals_timelock: Timestamp = field(default_factory=lambda: Timestamps.ZERO)
    rage_quit_timelock_started_at: Timestamp = field(default_factory=lambda: Timestamps.ZERO)

    min_withdrawal_request_amount: int = field(default_factory=lambda: 0)
    max_withdrawal_request_amount: int = field(default_factory=lambda: 0)
    min_withdrawal_batch_size: int = 8
    max_withdrawal_batch_size: int = 128

    accounting: AssetsAccounting = None
    batches_queue: WithdrawalsBatchesQueue = field(default_factory=lambda: WithdrawalsBatchesQueue())
    lido: Lido = None
    dual_governance: any = None
    time_manager: TimeManager = None
    withdrawal_queue: WithdrawalQueue = None

    signaling_escrow_min_lock_time: timedelta = default(timedelta(hours=5))

    def initialize(self, address, lido: Lido, dual_governance: any, time_manager: TimeManager):
        accounting = AssetsAccounting()
        accounting.initialize(time_manager)
        self.accounting = accounting

        self.address = address
        self.state = EscrowState.SignallingEscrow

        self.lido = lido
        self.dual_governance = dual_governance
        self.time_manager = time_manager

        self.lido.approve(self.address, self.lido.wstETH.address, self.lido.wstETH.infinite_allowance)
        self.lido.approve(self.address, Address.withdrawal_queue, self.lido.wstETH.infinite_allowance)

        withdrawal_queue = WithdrawalQueue()
        withdrawal_queue.initialize(time_manager, lido, Address.withdrawal_queue)
        withdrawal_queue.resume()

        self.withdrawal_queue = withdrawal_queue
        self.min_withdrawal_request_amount = withdrawal_queue.MIN_STETH_WITHDRAWAL_AMOUNT
        self.max_withdrawal_request_amount = withdrawal_queue.MAX_STETH_WITHDRAWAL_AMOUNT

    ## ---
    ## stETH token operations
    ## ---

    def lock_stETH(self, holder_addr: str, amount: int) -> int:
        self._check_escrow_state(EscrowState.SignallingEscrow)
        locked_stETH_shares = self.lido.get_shares_by_pooled_eth(amount)
        shares_value: SharesValue = SharesValue.from_uint256(amount)

        self.accounting.accountStETHSharesLock(holder_addr, shares_value)
        self.lido.transferSharesFrom(holder_addr, self.address, self.address, locked_stETH_shares)
        self._activate_next_governance_state()

    def unlock_stETH(self, holder_addr: str) -> int:
        self._check_escrow_state(EscrowState.SignallingEscrow)
        self._activate_next_governance_state()
        self.accounting.checkAssetsUnlockDelayPassed(holder_addr, self.signaling_escrow_min_lock_time.total_seconds())

        shares = self.accounting.state.assets[holder_addr].stETHLockedShares

        self.accounting.accountStETHSharesUnlock(holder_addr, shares)
        self.lido.transferShares(self.address, holder_addr, shares.value)
        self._activate_next_governance_state()

        return shares

    ## ---
    ## wstETH token operations
    ## ---

    def lock_wstETH(self, holder_addr: str, amount: int) -> int:
        self._check_escrow_state(EscrowState.SignallingEscrow)
        self.lido.wstETH_transferFrom(holder_addr, self.address, self.address, amount)
        stETH_shares = self.lido.unwrap(self.address, amount)
        locked_stETH_shares = self.lido.get_shares_by_pooled_eth(stETH_shares)
        shares_value: SharesValue = SharesValue.from_uint256(locked_stETH_shares)

        self.accounting.accountStETHSharesLock(holder_addr, shares_value)
        self._activate_next_governance_state()

    def unlock_wstETH(self, holder_addr: str) -> int:
        self._check_escrow_state(EscrowState.SignallingEscrow)
        self._activate_next_governance_state()
        self.accounting.checkAssetsUnlockDelayPassed(holder_addr, self.signaling_escrow_min_lock_time.total_seconds())

        shares = self.accounting.state.assets[holder_addr].stETHLockedShares
        self.accounting.accountStETHSharesUnlock(holder_addr, shares)
        unlocked_stETH_shares = self.lido.wrap(self.address, self.lido.get_pooled_eth_by_shares(shares.value))
        self.lido.wstETH_transfer(self.address, holder_addr, unlocked_stETH_shares)
        self._activate_next_governance_state()

    ## ---
    ## unstETH lock/unlock
    ## ---

    def lock_unstETH(self, holder: str, unstETH_ids: List[int]):
        self._check_escrow_state(EscrowState.SignallingEscrow)
        statuses = self.withdrawal_queue.get_withdrawal_status(unstETH_ids)
        self.accounting.accountUnstETHLock(holder, unstETH_ids, statuses)

        for unstETH_id in unstETH_ids:
            self.withdrawal_queue.transferFrom(holder, holder, self.address, unstETH_id)

        self._activate_next_governance_state()

    def unlock_unstETH(self, holder: str, unstETH_ids: List[int]):
        self._check_escrow_state(EscrowState.SignallingEscrow)
        self._activate_next_governance_state()
        self.accounting.checkAssetsUnlockDelayPassed(holder, self.signaling_escrow_min_lock_time.total_seconds())
        self.accounting.accountUnstETHUnlock(holder, unstETH_ids)

        for unstETH_id in unstETH_ids:
            self.withdrawal_queue.transferFrom(self.address, self.address, holder, unstETH_id)

        self._activate_next_governance_state()

    def mark_unstETH_finalized(self, unstETH_ids: List[int], hints: List[int]):
        self._check_escrow_state(EscrowState.SignallingEscrow)

        claimable_amounts = self.withdrawal_queue.get_claimable_ether(unstETH_ids, hints)
        self.accounting.accountUnstETHFinalized(unstETH_ids, claimable_amounts)

    ## ---
    ## Convert to NFT
    ## ---

    def request_withdrawals(self, holder: str, stETH_amounts: List[int]) -> List[int]:
        self._check_escrow_state(EscrowState.SignallingEscrow)
        unstETH_ids = self.withdrawal_queue.request_withdrawals(self.address, stETH_amounts, self.address)
        statuses = self.withdrawal_queue.get_withdrawal_status(unstETH_ids)

        total_shares: int = 0

        for status in statuses:
            total_shares += status.amount_of_shares

        self.accounting.accountStETHSharesUnlock(holder, SharesValue.from_uint256(total_shares))
        self.accounting.accountUnstETHLock(holder, unstETH_ids, statuses)

    def request_next_withdrawals_batch(self, max_batch_size: int):
        self._check_escrow_state(EscrowState.RageQuitEscrow)
        self.batches_queue.check_opened()

        if max_batch_size < self.min_withdrawal_batch_size or max_batch_size > self.max_withdrawal_batch_size:
            raise Errors.InvalidBatchSize

        remaining_stETH = self.lido.balance_of(self.address)

        if remaining_stETH < self.min_withdrawal_request_amount:
            return self.batches_queue.close()

        request_amounts = self.batches_queue.calc_request_amounts(
            self.min_withdrawal_request_amount,
            self.max_withdrawal_request_amount,
            min(remaining_stETH, (self.max_withdrawal_request_amount * max_batch_size)),
        )

        self.batches_queue.add(self.withdrawal_queue.request_withdrawals(self.address, request_amounts, self.address))

    def claim_next_withdrawals_batch(self, max_unstETH_ids_count: int):
        self._check_escrow_state(EscrowState.RageQuitEscrow)

        if self.rage_quit_timelock_started_at.is_not_zero():
            raise Errors.ClaimingIsFinished

        unstETH_ids = self.batches_queue.claim_next_batch(max_unstETH_ids_count)
        hints = self.withdrawal_queue.find_checkpoint_hints(
            unstETH_ids, 1, self.withdrawal_queue.get_last_checkpoint_index()
        )

        self._claim_next_withdrawals_batch(unstETH_ids, hints)

    def claim_next_withdrawals_batch_with_hints(self, from_unstETH_id: int, hints: List[int]):
        self._check_escrow_state(EscrowState.RageQuitEscrow)

        if self.rage_quit_timelock_started_at.is_not_zero():
            raise Errors.ClaimingIsFinished

        unstETH_ids = self.batches_queue.claim_next_batch(len(hints))

        if len(unstETH_ids) > 0 and from_unstETH_id != unstETH_ids[0]:
            raise Errors.UnexpectedUnstETHId

        if len(hints) != len(unstETH_ids):
            Errors.InvalidHintsLength

        self._claim_next_withdrawals_batch(unstETH_ids, hints)

    def claim_unstETH(self, unstETH_ids: List[int], hints: List[int]):
        self._check_escrow_state(EscrowState.RageQuitEscrow)

        claimable_amounts = self.withdrawal_queue.get_claimable_ether(unstETH_ids, hints)
        self.withdrawal_queue.claim_withdrawals(self.address, unstETH_ids, hints)
        total_amount_claimed = self.accounting.accountUnstETHClaimed(unstETH_ids, claimable_amounts)

        return total_amount_claimed

    ## ---
    ## Withdraw Logic
    ## ---

    def withdraw_ETH(self, holder: str) -> ETHValue:
        self._check_escrow_state(EscrowState.RageQuitEscrow)
        self._check_withdrawals_timelock_passed()
        eth_to_withdraw = self.accounting.accountStETHSharesWithdraw(holder)

        return eth_to_withdraw

    def withdraw_eth_from_unstETH_ids(self, holder: str, unstETH_ids: List[int]) -> ETHValue:
        self._check_escrow_state(EscrowState.RageQuitEscrow)
        self._check_withdrawals_timelock_passed()
        eth_to_withdraw = self.accounting.accountUnstETHWithdraw(holder, unstETH_ids)

        return eth_to_withdraw

    ## ---
    ## Getters
    ## ---

    def get_rage_quit_support(self) -> int:
        stETH_totals = self.accounting.state.stETHTotals
        unstETH_totals = self.accounting.state.unstETHTotals

        finalized_ETH = unstETH_totals.finalizedETH
        unfinalized_shares = stETH_totals.lockedShares + unstETH_totals.unfinalizedShares

        left = self.lido.get_pooled_eth_by_shares(unfinalized_shares.value) + finalized_ETH.value
        right = self.lido.get_total_supply() + finalized_ETH.value

        return int(ether_base * left / right)

    def get_locked_assets_totals(self) -> LockedAssetsTotal:
        stETH_totals = self.accounting.state.stETHTotals
        unstETH_totals = self.accounting.state.unstETHTotals

        return LockedAssetsTotal(
            stETH_locked_shares=stETH_totals.lockedShares.to_uint256(),
            stETH_claimed_ETH=stETH_totals.claimedETH.to_uint256(),
            unstETH_unfinalized_shares=unstETH_totals.unfinalizedShares.to_uint256(),
            unstETH_finalized_ETH=unstETH_totals.finalizedETH.to_uint256(),
        )

    def get_vetoer_state(self, vetoer: str) -> VetoerState:
        assets = self.accounting.state.assets[vetoer]

        return VetoerState(
            stETH_locked_shares=assets.stETHLockedShares.to_uint256(),
            unstETH_locked_shares=assets.unstETHLockedShares.to_uint256(),
            last_assets_lock_timestamp=assets.lastAssetsLockTimestamp.to_seconds(),
            unstETH_ids_count=len(assets.unstETHIds),
        )

    def get_next_withdrawal_batch(self, limit: int) -> List[int]:
        return self.batches_queue.get_next_withdrawals_batches(limit)

    def is_withdrawal_batches_finalized(self) -> bool:
        return self.batches_queue.is_closed()

    def is_withdrawals_claimed(self) -> bool:
        return not self.rage_quit_timelock_started_at.is_zero()

    def get_rage_quit_timelock_started_at(self) -> Timestamp:
        return self.rage_quit_timelock_started_at

    ## ---
    ## Rage Quit Extension delay
    ## ---

    def start_rage_quit_extension_delay(self):
        if not self.batches_queue.is_closed:
            raise Errors.BatchQueueIsNotClosed

        if not self.batches_queue.is_all_unstETH_claimed():
            raise Errors.UnclaimedBatches

        self.rage_quit_timelock_started_at = self.time_manager.get_current_timestamp_value()

    ## ---
    ## Escrow state update functions
    ## ---

    def start_rage_quit(self, extensionDelay: Timestamp, withdrawalsTimelock: Timestamp):
        self._check_escrow_state(EscrowState.SignallingEscrow)

        self.batches_queue.open()
        self.state = EscrowState.RageQuitEscrow
        self.rage_quit_extension_delay = extensionDelay
        self.rage_quit_withdrawals_timelock = withdrawalsTimelock

    def is_rage_quit_finalized(self):
        return (
            (self.state == EscrowState.RageQuitEscrow)
            & self.batches_queue.is_closed()
            & (self.rage_quit_timelock_started_at == Timestamps.ZERO)
            & (
                self.time_manager.get_current_timestamp_value()
                > (self.rage_quit_extension_delay + self.rage_quit_timelock_started_at)
            )
        )

    ## ---
    ## Internal methods
    ## ---

    def _activate_next_governance_state(self):
        self.dual_governance.activate_next_state()

    def _check_escrow_state(self, expected_state: EscrowState):
        if self.state != expected_state:
            raise Errors.InvalidState

    def _claim_next_withdrawals_batch(self, unstETH_ids: List[int], hints: List[int]):
        total_claimed = self.withdrawal_queue.claim_withdrawals(self.address, unstETH_ids, hints)

        if total_claimed > 0:
            self.accounting.accountClaimedStETH(ETHValue.from_uint256(total_claimed))

        if self.batches_queue.is_closed() and self.batches_queue.is_all_unstETH_claimed():
            self.rage_quit_timelock_started_at = self.time_manager.get_current_timestamp_value()

    def _check_withdrawals_timelock_passed(self):
        if self.rage_quit_timelock_started_at.is_zero():
            raise Errors.RageQuitExtraTimelockNotStarted

        withdrawals_timelock = self.rage_quit_extension_delay + self.rage_quit_withdrawals_timelock

        if self.time_manager.get_current_timestamp_value() <= withdrawals_timelock + self.rage_quit_timelock_started_at:
            raise Errors.WithdrawalsTimelockNotPassed

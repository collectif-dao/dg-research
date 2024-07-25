from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum

from specs.escrow.accounting import AssetsAccounting
from specs.escrow.withdrawal_batches import WithdrawalsBatchesQueue
from specs.lido import Lido
from specs.time_manager import TimeManager
from specs.types.shares_value import SharesValue
from specs.types.timestamp import Timestamp, Timestamps
from specs.utils import default, ether_base

from .errors import Errors


class EscrowState(Enum):
    NotInitialized = 1
    SignallingEscrow = 2
    RageQuitEscrow = 3


@dataclass
class Escrow:
    MASTER_COPY: str = field(default_factory=lambda: "")
    state: EscrowState = EscrowState.NotInitialized

    rage_quit_extension_delay: Timestamp = field(default_factory=lambda: Timestamps.ZERO)
    rage_quit_withdrawals_timelock: Timestamp = field(default_factory=lambda: Timestamps.ZERO)
    rage_quit_timelock_started_at: Timestamp = field(default_factory=lambda: Timestamps.ZERO)

    accounting: AssetsAccounting = None
    batches_queue: WithdrawalsBatchesQueue = field(default_factory=lambda: WithdrawalsBatchesQueue())
    lido: Lido = None
    dual_governance: any = None
    time_manager: TimeManager = None

    signaling_escrow_min_lock_time: timedelta = default(timedelta(hours=5))

    def initialize(self, address, lido: Lido, dual_governance: any, time_manager: TimeManager):
        accounting = AssetsAccounting()
        accounting.initialize(time_manager)
        self.accounting = accounting

        self.MASTER_COPY = address
        self.state = EscrowState.SignallingEscrow

        self.lido = lido
        self.dual_governance = dual_governance
        self.time_manager = time_manager

    ## ---
    ## stETH token operations
    ## ---

    def lock_stETH(self, holder_addr: str, amount: int) -> int:
        locked_stETH_shares = self.lido.get_shares_by_pooled_eth(amount)
        shares_value: SharesValue = SharesValue.from_uint256(amount)

        self.accounting.accountStETHSharesLock(holder_addr, shares_value)
        self.lido.transferSharesFrom(holder_addr, self._address_this, locked_stETH_shares)
        self._activate_next_governance_state()

    def unlock_stETH(self, holder_addr: str) -> int:
        self._activate_next_governance_state()
        self.accounting.checkAssetsUnlockDelayPassed(holder_addr, self.signaling_escrow_min_lock_time.total_seconds())

        shares = self.accounting.state.assets[holder_addr].stETHLockedShares

        self.accounting.accountStETHSharesUnlock(holder_addr, shares)
        self.lido.transferShares(holder_addr, shares.value)
        self._activate_next_governance_state()

    ## ---
    ## wstETH token operations
    ## ---

    def lock_wstETH(self, holder_addr: str, amount: int) -> int:
        self.lido.wstETH_transferFrom(holder_addr, self._address_this, amount)
        stETH_shares = self.lido.unwrap(amount)
        locked_stETH_shares = self.lido.get_shares_by_pooled_eth(stETH_shares)
        shares_value: SharesValue = SharesValue.from_uint256(locked_stETH_shares)

        self.accounting.accountStETHSharesLock(holder_addr, shares_value)
        self._activate_next_governance_state()

    def unlock_wstETH(self, holder_addr: str) -> int:
        self._activate_next_governance_state()
        self.accounting.checkAssetsUnlockDelayPassed(holder_addr, self.signaling_escrow_min_lock_time.total_seconds())

        shares = self.accounting.state.assets[holder_addr].stETHLockedShares
        self.accounting.accountStETHSharesUnlock(holder_addr, shares)
        unlocked_stETH_shares = self.lido.wrap(self.lido.get_pooled_eth_by_shares(shares.value))
        self.lido.wstETH_transfer(holder_addr, unlocked_stETH_shares)
        self._activate_next_governance_state()

    def get_rage_quit_support(self) -> int:
        stETH_totals = self.accounting.state.stETHTotals
        unstETH_totals = self.accounting.state.unstETHTotals

        finalized_ETH = unstETH_totals.finalizedETH
        unfinalized_shares = stETH_totals.lockedShares + unstETH_totals.unfinalizedShares

        left = self.lido.get_pooled_eth_by_shares(unfinalized_shares.value) + finalized_ETH.value
        right = self.lido.get_total_supply() + finalized_ETH.value

        return ether_base * left / right

    ## ---
    ## Escrow state update functions
    ## ---

    def start_rage_quit(self, extensionDelay: int, withdrawalsTimelock: int):
        self._check_escrow_state(EscrowState.SignallingEscrow)

        self.batches_queue.open()
        self.state = EscrowState.RageQuitEscrow
        self.rage_quit_extension_delay = Timestamps.from_uint256(extensionDelay)
        self.rage_quit_withdrawals_timelock = Timestamps.from_uint256(withdrawalsTimelock)

    def is_rage_quit_finalized(self):
        return (
            (self.state == EscrowState.RageQuitEscrow)
            & self.batches_queue.is_closed()
            & (self.rage_quit_timelock_started_at == Timestamps.ZERO)
            & (
                self.time_manager.get_current_timestamp()
                > (self.rage_quit_extension_delay.value + self.rage_quit_timelock_started_at.value)
            )
        )

    def _activate_next_governance_state(self):
        self.dual_governance.activate_next_state()

    def _check_escrow_state(self, expected_state: EscrowState):
        if self.state != expected_state:
            raise Errors.InvalidState

    def _address_this(self) -> str:
        return self.MASTER_COPY

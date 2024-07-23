from dataclasses import dataclass
from datetime import timedelta
from enum import Enum

from specs.escrow.accounting import AssetsAccounting
from specs.escrow.withdrawal_batches import WithdrawalsBatchesQueue
from specs.lido import Lido
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
    MASTER_COPY: str = ""
    state: EscrowState = EscrowState.NotInitialized

    staked_stETH: int = 0
    finalized_ETH: int = 0
    total_supply: int = 0

    rage_quit_extension_delay: Timestamp = Timestamps.ZERO
    rage_quit_withdrawals_timelock: Timestamp = Timestamps.ZERO
    rage_quit_timelock_started_at: Timestamp = Timestamps.ZERO

    accounting: AssetsAccounting = AssetsAccounting()
    batches_queue: WithdrawalsBatchesQueue = WithdrawalsBatchesQueue()
    lido: Lido = None
    dual_governance: any = None

    signaling_escrow_min_lock_time: timedelta = default(timedelta(hours=5))

    def initialize(
        self,
        address,
        supply,
        # accounting: AssetsAccounting,
        # queue: WithdrawalsBatchesQueue,
        lido: Lido,
        dual_governance: any,
    ):
        self.MASTER_COPY = address
        self.total_supply = supply
        self.state = EscrowState.SignallingEscrow

        # self.accounting = accounting
        # self.batches_queue = queue

        self.lido = lido
        self.dual_governance = dual_governance

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
        self.accounting.checkAssetsUnlockDelayPassed(holder_addr, self.signaling_escrow_min_lock_time)

        unlocked_stETH_shares = self.accounting.accountStETHSharesUnlock(holder_addr)
        self.lido.transferShares(holder_addr, unlocked_stETH_shares.value)
        self._activate_next_governance_state()

    ## ---
    ## wstETH token operations
    ## ---

    def get_rage_quit_support(self) -> int:
        stETH_totals = self.accounting.state.stETHTotals
        unstETH_totals = self.accounting.state.unstETHTotals

        finalized_ETH = unstETH_totals.finalizedETH
        unfinalized_shares = stETH_totals.lockedShares + unstETH_totals.unfinalizedShares

        # print("finalized_ETH is", finalized_ETH.value)
        # print("unfinalized_shares is", unfinalized_shares.value)

        left = self.lido.get_pooled_eth_by_shares(unfinalized_shares.value) + finalized_ETH.value
        right = self.lido.get_total_supply() + finalized_ETH.value

        # print("left side is", left)
        # print("right side is", right)

        return ether_base * left / right

    def start_rage_quit(self, extensionDelay, withdrawalsTimelock):
        self._check_escrow_state(EscrowState.SignallingEscrow)

        self.batches_queue.open()
        self.state = EscrowState.RageQuitEscrow
        self.rage_quit_extension_delay = extensionDelay
        self.rage_quit_withdrawals_timelock = withdrawalsTimelock

    def is_rage_quit_finalized(self):
        return (
            self.state
            == EscrowState.RageQuitEscrow & self.batches_queue.is_closed() & self.rage_quit_timelock_started_at
            == Timestamps.ZERO & Timestamps.now()
            > (self.rage_quit_extension_delay + self.rage_quit_timelock_started_at)
        )

    def _activate_next_governance_state(self):
        self.dual_governance.activate_next_state()

    def _check_escrow_state(self, expected_state: EscrowState):
        if self.state != expected_state:
            raise Errors.InvalidState

    def _address_this(self) -> str:
        return self.MASTER_COPY

    def finalizeETH(self, amount):
        self.finalized_ETH += amount

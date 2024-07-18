from dataclasses import dataclass
from enum import Enum

from ..utils import ether_base

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
    rage_quit_extension_delay: int = 0
    rage_quit_withdrawals_timelock: int = 0

    def initialize(self, address, supply):
        self.MASTER_COPY = address
        self.total_supply = supply
        self.state = EscrowState.SignallingEscrow

    def get_rage_quit_support(self):
        left = self.staked_stETH + self.finalized_ETH
        right = self.total_supply + self.finalized_ETH

        return (ether_base * left) / right

    def start_rage_quit(self, extensionDelay, withdrawalsTimelock):
        if self.state != EscrowState.SignallingEscrow:
            raise Errors.InvalidState

        self.state = EscrowState.RageQuitEscrow
        self.rage_quit_extension_delay = extensionDelay
        self.rage_quit_withdrawals_timelock = withdrawalsTimelock

    def is_rage_quit_finalized(self):
        return True

    def stake_stETH(self, amount):
        self.staked_stETH += amount

    def finalizeETH(self, amount):
        self.finalized_ETH += amount

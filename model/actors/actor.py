from dataclasses import dataclass, field
from enum import Enum

from specs.utils import *


class NotAnoughtActorBalanceExeption(Exception):
    pass


class ReactionTime(Enum):
    Normal = 1
    Quick = 2
    Slow = 3


class GovernanceParticipation(Enum):
    Normal = 1
    Full = 2
    Abstaining = 3


@dataclass
class BaseActor:
    address: str = field(default_factory=lambda: "")
    ldo_balance: int = 0
    st_eth_balance: int = 0
    st_eth_locked: int = 0
    reaction_time: ReactionTime = field(default_factory=lambda: ReactionTime.Normal)
    governance_participation: GovernanceParticipation = field(default_factory=lambda: GovernanceParticipation.Normal)

    def initialize(self, ldo, st_eth):
        self.ldo_balance = ldo
        self.st_eth_balance = st_eth
        self.address = generate_address()

    def get_tocken_ratio(self):
        return (self.st_eth_balance + self.st_eth_locked) / self.ldo_balance

    def stake_to_escrow(self, amount):
        if self.st_eth_balance < amount:
            raise NotAnoughtActorBalanceExeption

        self.st_eth_balance = self.st_eth_balance - amount
        self.st_eth_locked = self.st_eth_locked + amount

    def unstake_from_escrow(self, amount):
        if self.st_eth_locked < amount:
            raise NotAnoughtActorBalanceExeption

        self.st_eth_balance = self.st_eth_balance + amount
        self.st_eth_locked = self.st_eth_locked - amount

    def will_change_escrow(self, dg):
        return 0

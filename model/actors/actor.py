from dataclasses import dataclass, field
from typing import List, Set, Tuple

import numpy as np

from model.actors.errors import NotEnoughActorStETHBalance, NotEnoughActorWstETHBalance
from model.types.actors import ActorType
from model.types.escrow import ActorLockAmounts
from model.types.governance_goals import GovernanceGoal
from model.types.governance_participation import GovernanceParticipation
from model.types.proposal_type import ProposalType
from model.types.proposals import Proposal, ProposalSubType
from model.types.reaction_time import ReactionTime
from model.utils.reactions import calculate_reaction_delay
from specs.dual_governance import DualGovernance
from specs.time_manager import TimeManager
from specs.utils import generate_address


@dataclass
class BaseActor:
    id: int = 0
    actor_type: ActorType = ActorType.BaseActor
    address: str = field(default_factory=lambda: "")
    entity: str = ""

    ldo_balance: int = 0

    st_eth_balance: int = 0
    initial_st_eth_balance: int = 0
    st_eth_locked: int = 0

    wstETH_balance: int = 0
    initial_wstETH_balance: int = 0
    wstETH_locked: int = 0

    hypothetical_stETH_balance: int = 0
    hypothetical_wstETH_balance: int = 0

    last_locked_tx_timestamp: int = 0

    starting_health: int = 0
    health: int = 0
    total_damage: int = 0
    total_recovery: int = 0

    governance_goal: GovernanceGoal = field(default_factory=lambda: GovernanceGoal.Neutrality)

    reaction_time: ReactionTime = field(default_factory=lambda: ReactionTime.Normal)
    governance_participation: GovernanceParticipation = field(default_factory=lambda: GovernanceParticipation.Normal)

    def initialize(
        self,
        id: int,
        entity: str,
        address: str,
        health: int,
        ldo: int,
        stETH: int,
        wstETH: int,
        reaction_time=ReactionTime.Normal,
        governance_participation: GovernanceParticipation = GovernanceParticipation.Normal,
    ):
        self.id = id
        self.entity = entity
        self.starting_health = health
        self.health = health
        self.initial_health = health
        self.ldo_balance = ldo
        self.st_eth_balance = stETH
        self.initial_st_eth_balance = stETH
        self.hypothetical_stETH_balance = stETH
        self.wstETH_balance = wstETH
        self.hypothetical_wstETH_balance = wstETH
        self.initial_wstETH_balance = wstETH
        self.reaction_time = reaction_time
        self.governance_participation = governance_participation

        if address == "":
            self.address = generate_address()
        else:
            self.address = address

    def get_token_ratio(self):
        return (self.st_eth_balance + self.st_eth_locked) / self.ldo_balance

    def lock_to_escrow(self, amounts: ActorLockAmounts, time_manager: TimeManager):
        if self.st_eth_balance < amounts.stETH_amount:
            raise NotEnoughActorStETHBalance

        if self.wstETH_balance < amounts.wstETH_amount:
            raise NotEnoughActorWstETHBalance

        self.last_locked_tx_timestamp = time_manager.get_current_timestamp()

        self.st_eth_balance = self.st_eth_balance - amounts.stETH_amount
        self.st_eth_locked = self.st_eth_locked + amounts.stETH_amount

        self.wstETH_balance = self.wstETH_balance - amounts.wstETH_amount
        self.wstETH_locked = self.wstETH_locked + amounts.wstETH_amount

    def unlock_from_escrow(self, amounts: ActorLockAmounts, time_manager: TimeManager):
        if self.st_eth_locked < amounts.stETH_amount:
            raise NotEnoughActorStETHBalance

        if self.wstETH_locked < amounts.wstETH_amount:
            raise NotEnoughActorWstETHBalance

        self.last_locked_tx_timestamp = time_manager.get_current_timestamp()

        self.st_eth_balance = self.st_eth_balance - amounts.stETH_amount
        self.st_eth_locked = self.st_eth_locked + amounts.stETH_amount

        self.wstETH_balance = self.wstETH_balance - amounts.wstETH_amount
        self.wstETH_locked = self.wstETH_locked + amounts.wstETH_amount

    def rebalance_to_stETH(self, amounts: ActorLockAmounts, time_manager: TimeManager):
        if (self.st_eth_locked + self.wstETH_locked) + (amounts.stETH_amount + amounts.wstETH_amount) < 0:
            raise NotEnoughActorStETHBalance

        self.last_locked_tx_timestamp = time_manager.get_current_timestamp()

        # print("rebalancing wstETH into stETH")

        # print("amounts.stETH_amount", amounts.stETH_amount)
        # print("amounts.wstETH_amount", amounts.wstETH_amount)

        # print("self.st_eth_balance before", self.st_eth_balance)
        # print("self.st_eth_locked before", self.st_eth_locked)
        # print("self.wstETH_locked before", self.wstETH_locked)
        # print("self.wstETH_balance before", self.wstETH_balance)

        self.st_eth_balance = (self.st_eth_balance - amounts.stETH_amount) - amounts.wstETH_amount
        self.st_eth_locked = self.st_eth_locked + amounts.stETH_amount
        self.wstETH_locked = self.wstETH_locked + amounts.wstETH_amount

        # print("self.st_eth_balance after", self.st_eth_balance)
        # print("self.st_eth_locked after", self.st_eth_locked)
        # print("self.wstETH_locked after", self.wstETH_locked)
        # print("self.wstETH_balance after", self.wstETH_balance)

    def update_actor_health(self, damage: int = 0):
        if damage > 0:
            if self.health - damage < 0:
                damage = self.health
            self.total_damage += damage

        elif self.total_damage > 0 and damage < 0:
            if self.total_damage + damage < 0:
                damage = -self.total_damage
            self.total_recovery -= damage

            if self.total_recovery > self.total_damage:
                self.total_recovery = self.total_damage

        self.health -= damage

        if self.total_damage > 0:
            max_recoverable_health = self.total_damage
            if self.health > max_recoverable_health:
                self.health = max_recoverable_health

        if self.health > 100:
            self.health = 100

        self.update_reaction_delay()

    def simulate_proposal_effect(self, proposal: Proposal):
        if self.entity == "Contract" and proposal.proposal_type != ProposalType.Hack:
            self.hypothetical_stETH_balance = self.st_eth_balance
            self.hypothetical_wstETH_balance = self.wstETH_balance
        else:
            match proposal.sub_type:
                case ProposalSubType.NoEffect:
                    self.hypothetical_stETH_balance = self.st_eth_balance
                    self.hypothetical_wstETH_balance = self.wstETH_balance

                case ProposalSubType.FundsStealing:
                    if self.address in proposal.attack_targets or len(proposal.attack_targets) == 0:
                        self.hypothetical_stETH_balance = 0
                        self.hypothetical_wstETH_balance = 0

    def after_simulate_proposal_effect(self):
        if (
            self.hypothetical_stETH_balance < self.initial_st_eth_balance
            or self.hypothetical_wstETH_balance < self.initial_wstETH_balance
        ):
            self.health = 0
        elif (
            self.hypothetical_stETH_balance > self.initial_st_eth_balance
            or self.hypothetical_wstETH_balance > self.initial_wstETH_balance
        ):
            total_initial_balance = self.initial_st_eth_balance + self.initial_wstETH_balance
            total_hypothetical_balance = self.hypothetical_stETH_balance + self.hypothetical_wstETH_balance
            total_balance_increase = total_hypothetical_balance - total_initial_balance

            if total_initial_balance > 0:
                multiplier = 1 + (total_balance_increase / total_initial_balance)
                multiplier = min(multiplier, 2)
            else:
                multiplier = 1

            self.health *= multiplier

    def after_reset_proposal_effect(self):
        if (
            self.hypothetical_stETH_balance == self.initial_st_eth_balance
            and self.hypothetical_wstETH_balance == self.initial_wstETH_balance
        ):
            self.health = self.initial_health

    def update_reaction_delay(self):
        samples = np.random.lognormal(mean=1, sigma=0.5, size=1000)
        reaction_delay = calculate_reaction_delay(samples, self.reaction_time)
        self.reaction_delay = reaction_delay

    def reset_proposal_effect(self):
        self.hypothetical_stETH_balance = self.initial_st_eth_balance
        self.hypothetical_wstETH_balance = self.initial_wstETH_balance

    def calculate_lock_amount(self, dual_governance: DualGovernance, proposals: List[Proposal]) -> Tuple[int, int]:
        return (0, 0)

    def is_coordinated_attacker(self, coordinated_attackers: Set[str]) -> bool:
        return self.address in coordinated_attackers

    def attack_honest_actors(self, proposal: Proposal, stETH_gain_per_attacker: float, wstETH_gain_per_attacker: float):
        pass

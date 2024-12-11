from dataclasses import dataclass, field
from typing import Dict, List, Set

import numpy as np

from model.types.actors import ActorType
from model.types.proposal_type import ProposalSubType, ProposalType
from model.types.scenario import Scenario
from model.utils.proposals import determine_proposal_damage, determine_proposal_subtype, determine_proposal_type


@dataclass
class ProposalsEffect:
    effects: Dict[str, int] = field(default_factory=dict)

    def add_effect(self, label: str, value: int):
        self.effects[label] = value

    def get_effect(self, label: str) -> int:
        return self.effects.get(label, 0)


@dataclass
class Proposal:
    id: int = 0
    timestep: int = 0
    damage: int = 0
    effects: ProposalsEffect = field(default_factory=ProposalsEffect)
    proposer: str = field(default_factory=lambda: "")
    proposal_type: ProposalType = field(default_factory=lambda: ProposalType.NoImpact)
    sub_type: ProposalSubType = field(default_factory=lambda: ProposalSubType.NoEffect)
    attack_targets: Set[str] = field(default_factory=lambda: set())
    attack_targets_determination: bool = False
    cancelable: bool = True
    damage_amounts: np.ndarray = None
    is_active: bool = False
    stETH_changes: np.ndarray = None  # Tracks stETH changes per actor
    wstETH_changes: np.ndarray = None  # Tracks wstETH changes per actor

    def store_damage_effect(self, damage_amounts: np.ndarray):
        """Store only damage amounts - zeros implicitly represent the mask"""
        self.damage_amounts = damage_amounts.copy()
        self.is_active = True

    def get_damage_mask(self) -> np.ndarray:
        """Get mask of actors that received damage"""
        return self.damage_amounts != 0 if self.damage_amounts is not None else None

    def clear_damage_effect(self):
        self.damage_amounts = None
        self.is_active = False

    def register_fund_changes(
        self,
        actors_amount: int,
        victims_mask: np.ndarray,
        victims_stETH: np.ndarray,
        victims_wstETH: np.ndarray,
        attackers_mask: np.ndarray = None,
    ):
        if self.stETH_changes is None:
            self.stETH_changes = np.zeros_like(actors_amount)
        if self.wstETH_changes is None:
            self.wstETH_changes = np.zeros_like(actors_amount)

        self.stETH_changes[victims_mask] = -victims_stETH[victims_mask]
        self.wstETH_changes[victims_mask] = -victims_wstETH[victims_mask]

        total_stolen_stETH = np.sum(victims_stETH[victims_mask])
        total_stolen_wstETH = np.sum(victims_wstETH[victims_mask])

        if attackers_mask is not None:
            num_attackers = np.sum(attackers_mask)
            if num_attackers > 0:
                stETH_per_attacker = total_stolen_stETH / num_attackers
                wstETH_per_attacker = total_stolen_wstETH / num_attackers

                self.stETH_changes[attackers_mask] = stETH_per_attacker
                self.wstETH_changes[attackers_mask] = wstETH_per_attacker

    def register_bribe_changes(
        self,
        actors_amount: int,
        bribed_mask: np.ndarray,
        victims_mask: np.ndarray,
        attackers_mask: np.ndarray,
        current_stETH: np.ndarray,
        current_wstETH: np.ndarray,
    ):
        """Calculate and register both bribes and stolen funds"""
        if self.stETH_changes is None:
            self.stETH_changes = np.zeros_like(actors_amount)
        if self.wstETH_changes is None:
            self.wstETH_changes = np.zeros_like(actors_amount)

        self.stETH_changes[victims_mask] = -current_stETH[victims_mask]
        self.wstETH_changes[victims_mask] = -current_wstETH[victims_mask]

        total_stolen_stETH = np.sum(current_stETH[victims_mask])
        total_stolen_wstETH = np.sum(current_wstETH[victims_mask])

        honest_bribed_mask = bribed_mask & ~attackers_mask
        num_honest_bribed = np.sum(honest_bribed_mask)

        if num_honest_bribed > 0:
            honest_bribe_stETH = (total_stolen_stETH // 2) // num_honest_bribed
            honest_bribe_wstETH = (total_stolen_wstETH // 2) // num_honest_bribed

            self.stETH_changes[honest_bribed_mask] = honest_bribe_stETH
            self.wstETH_changes[honest_bribed_mask] = honest_bribe_wstETH

        if np.any(attackers_mask):
            num_attackers = np.sum(attackers_mask)
            attacker_share_stETH = (total_stolen_stETH // 2) // num_attackers
            attacker_share_wstETH = (total_stolen_wstETH // 2) // num_attackers

            self.stETH_changes[attackers_mask] = attacker_share_stETH
            self.wstETH_changes[attackers_mask] = attacker_share_wstETH

    def get_victims_mask(self, actors: any, include_contracts: bool = True) -> np.ndarray:
        """
        Centralized method to determine victims based on proposal and actor properties

        Parameters:
        - proposal: The proposal being evaluated
        - include_contracts: Whether to include contract entities as potential victims

        Returns:
        - numpy array boolean mask indicating which actors are victims
        """

        victims_mask = np.isin(
            actors.actor_type,
            [
                ActorType.HonestActor.value,
                ActorType.SingleDefender.value,
                ActorType.CoordinatedDefender.value,
            ],
        )

        attackers_mask = np.isin(
            actors.actor_type,
            [
                ActorType.SingleAttacker.value,
                ActorType.CoordinatedAttacker.value,
            ],
        )
        victims_mask &= ~attackers_mask

        if not include_contracts:
            victims_mask &= actors.entity != "Contract"

        if self.attack_targets:
            match self.sub_type:
                case ProposalSubType.FundsStealing:
                    victims_mask &= np.isin(actors.address, list(self.attack_targets))
                case ProposalSubType.Bribing:
                    victims_mask &= ~np.isin(actors.address, list(self.attack_targets))

        if self.sub_type == ProposalSubType.FundsStealing:
            victims_mask &= (actors.stETH > 0) | (actors.wstETH > 0)

        return victims_mask

    def __eq__(self, other):
        if (
            self.timestep == other.timestep
            and self.damage == other.damage
            and self.effects == other.effects
            and self.proposal_type == other.proposal_type
            and self.sub_type == other.sub_type
            and self.attack_targets == other.attack_targets
            and self.cancelable == other.cancelable
        ):
            return True
        return False


def new_proposal(
    timestep: int,
    id: int,
    proposer: str,
    scenario: Scenario,
    proposal_type: ProposalType = None,
    sub_type: ProposalSubType = None,
    attack_targets: set = {},
    cancelable: bool = True,
    effects: ProposalsEffect = ProposalsEffect(),
) -> Proposal:
    proposal = Proposal(
        id=id, timestep=timestep, proposal_type=proposal_type, sub_type=sub_type, cancelable=cancelable, effects=effects
    )
    proposal.proposer = proposer

    if proposal_type is None:
        proposal.proposal_type = determine_proposal_type(scenario)

    if sub_type is None:
        proposal.sub_type = determine_proposal_subtype(scenario)

    proposal.damage = determine_proposal_damage(proposal.proposal_type)
    proposal.attack_targets = attack_targets

    return proposal


def get_proposal_by_id(proposals: List[Proposal], id: int) -> Proposal:
    for proposal in proposals:
        if proposal.id == id:
            return proposal

    return None

import logging
from argparse import ArgumentError
from typing import List, Tuple

import numpy as np

from model import sys_params
from model.actors.errors import NotEnoughActorStETHBalance, NotEnoughActorWstETHBalance
from model.types.actors import ActorReaction, ActorType
from model.types.proposal_type import ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.scenario import Scenario
from model.utils.reactions import generate_initial_reaction_time_vector, generate_reaction_delay_vector
from specs.dual_governance import DualGovernance
from specs.dual_governance.proposals import ProposalStatus
from specs.dual_governance.state import State
from specs.utils import generate_address

logging.getLogger("numba").setLevel(logging.WARNING)


class Actors:
    def __init__(
        self,
        address: np.ndarray,
        entity: np.ndarray,
        ldo: np.ndarray,
        stETH: np.ndarray,
        wstETH: np.ndarray,
        label: np.ndarray,
        health: np.ndarray,
        actor_type: np.ndarray,
        reaction_time: np.ndarray,
        governance_participation: np.ndarray,
    ):
        n = len(address)
        if (
            (len(ldo) != n)
            or (len(stETH) != n)
            or (len(wstETH) != n)
            or (len(label) != n)
            or (len(entity) != n)
            or (len(health) != n)
            or (len(actor_type) != n)
            or (len(reaction_time) != n)
            or (len(governance_participation) != n)
        ):
            raise ArgumentError(message="All arrays must be the same length")
        self.amount = n

        self.address = address
        self.ldo = ldo
        self.stETH = stETH
        self.stETH_locked = np.zeros_like(self.stETH)
        self.initial_stETH = np.copy(self.stETH)
        self.hypothetical_stETH = np.copy(self.stETH)
        self.wstETH = wstETH
        self.wstETH_locked = np.zeros_like(self.wstETH)
        self.initial_wstETH = np.copy(self.wstETH)
        self.hypothetical_wstETH = np.copy(self.wstETH)
        self.label = label
        self.entity = entity
        self.health = health
        self.hypothetical_health = np.copy(self.health)
        self.cropped_health = np.copy(self.health)
        self.initial_health = np.copy(self.health)
        self.total_damage = np.zeros_like(self.health)
        self.total_healing = np.zeros_like(self.health)
        self.total_recovery = np.zeros_like(self.health)
        self.actor_type = actor_type
        self.reaction_time = reaction_time
        self.governance_participation = governance_participation

        self.next_hp_check_timestamp = generate_initial_reaction_time_vector(self.reaction_time)
        self.recovery_time = np.zeros_like(self.next_hp_check_timestamp)
        self.last_locked_tx_timestamp = np.zeros_like(self.next_hp_check_timestamp)

        empty_entity = self.entity == ""
        self.entity[empty_entity] = "Other"

        empty_address = self.address == ""
        self.address[empty_address] = [generate_address() for _ in range(np.sum(empty_address))]
        self.did_quit = np.zeros(self.amount, dtype=np.bool_)

    ## ---
    ## Funds movement section
    ## ---

    def lock_to_escrow(
        self, stETH_amounts: np.ndarray, wstETH_amounts: np.ndarray, current_timestamp: int, mask: np.ndarray
    ):
        if np.any(self.stETH[mask] < stETH_amounts[mask]):
            raise NotEnoughActorStETHBalance

        if np.any(self.wstETH[mask] < wstETH_amounts[mask]):
            raise NotEnoughActorWstETHBalance

        self.last_locked_tx_timestamp[mask] = current_timestamp

        self.stETH[mask] -= stETH_amounts[mask]
        self.stETH_locked[mask] += stETH_amounts[mask]
        self.hypothetical_stETH[mask] -= stETH_amounts[mask]

        self.wstETH[mask] -= wstETH_amounts[mask]
        self.wstETH_locked[mask] += wstETH_amounts[mask]
        self.hypothetical_wstETH[mask] -= wstETH_amounts[mask]

    def unlock_from_escrow(
        self, stETH_amounts: np.ndarray, wstETH_amounts: np.ndarray, current_timestamp: int, mask: np.ndarray
    ):
        if np.any(self.stETH_locked[mask] < np.abs(stETH_amounts[mask])):
            raise NotEnoughActorStETHBalance

        if np.any(self.wstETH_locked[mask] < np.abs(wstETH_amounts[mask])):
            raise NotEnoughActorWstETHBalance

        self.last_locked_tx_timestamp[mask] = current_timestamp

        self.stETH[mask] += np.abs(stETH_amounts[mask])
        self.stETH_locked[mask] -= np.abs(stETH_amounts[mask])
        self.hypothetical_stETH[mask] += np.abs(stETH_amounts[mask])

        self.wstETH[mask] += np.abs(wstETH_amounts[mask])
        self.wstETH_locked[mask] -= np.abs(wstETH_amounts[mask])
        self.hypothetical_wstETH[mask] += np.abs(wstETH_amounts[mask])

    def rebalance_to_stETH(
        self, stETH_amounts: np.ndarray, wstETH_amounts: np.ndarray, current_timestamp: int, mask: np.ndarray
    ):
        if np.any(
            (self.stETH_locked[mask] + self.wstETH_locked[mask])
            < (np.abs(stETH_amounts[mask]) + np.abs(wstETH_amounts[mask]))
        ):
            raise NotEnoughActorStETHBalance

        self.last_locked_tx_timestamp[mask] = current_timestamp

        total_amount = np.abs(stETH_amounts[mask]) + np.abs(wstETH_amounts[mask])
        self.stETH[mask] += total_amount
        self.stETH_locked[mask] -= np.abs(stETH_amounts[mask])
        self.wstETH_locked[mask] -= np.abs(wstETH_amounts[mask])
        self.hypothetical_stETH[mask] += total_amount
        self.hypothetical_wstETH[mask] -= np.abs(wstETH_amounts[mask])

    ## ---
    ## Proposal effects section
    ## ---

    def simulate_proposal_effect(
        self,
        proposal: Proposal,
        victims_mask: np.ndarray = None,
        attackers_mask: np.ndarray = None,
    ):
        if victims_mask is None:
            victims_mask = proposal.get_victims_mask(self, include_contracts=True)

        match proposal.sub_type:
            case ProposalSubType.FundsStealing:
                current_stETH = np.copy(self.hypothetical_stETH)
                current_wstETH = np.copy(self.hypothetical_wstETH)

                proposal.register_fund_changes(
                    actors_amount=self.amount,
                    victims_mask=victims_mask,
                    victims_stETH=current_stETH,
                    victims_wstETH=current_wstETH,
                    attackers_mask=attackers_mask,
                )

                self.hypothetical_stETH += proposal.stETH_changes
                self.hypothetical_wstETH += proposal.wstETH_changes

    def reset_proposal_effect(self, proposal: Proposal):
        """Reset only the changes from this specific proposal"""
        if hasattr(proposal, "stETH_changes") and hasattr(proposal, "wstETH_changes"):
            self.hypothetical_stETH -= proposal.stETH_changes
            self.hypothetical_wstETH -= proposal.wstETH_changes

    def finalize_proposal_effect(self, proposal: Proposal):
        """Finalize balance changes when a proposal is executed"""
        if not proposal.is_active:
            return

        if proposal.stETH_changes is not None:
            if np.sum(proposal.stETH_changes) > 0:
                self.stETH += proposal.stETH_changes

        if proposal.wstETH_changes is not None:
            if np.sum(proposal.wstETH_changes) > 0:
                self.wstETH += proposal.wstETH_changes

    ## ---
    ## Proposal damage section
    ## ---

    def apply_proposal_damage(self, current_timestamp: int, proposal: Proposal, mask: np.ndarray = None):
        if mask is None:
            mask = np.repeat(True, self.amount)

        initial_health = self.hypothetical_health.copy()
        damage = np.repeat(proposal.damage, self.amount)

        if proposal.sub_type == ProposalSubType.FundsStealing:
            if proposal.attack_targets:
                target_mask = np.isin(self.address, list(proposal.attack_targets))
                damage[target_mask] = sys_params.sys_params["max_damage"]
            else:
                target_mask = self.entity != "Contract"
                damage[target_mask] = sys_params.sys_params["max_damage"]

        for label, label_damage in proposal.effects.effects.items():
            if label_damage != 0:
                damage[self.label == label] = label_damage

        damage[np.logical_not(mask)] = 0

        self.hypothetical_health = initial_health - damage

        proposal.store_damage_effect(damage)

        damage_mask = damage != 0
        if np.any(damage_mask):
            damage_is_positive = damage > 0
            self.total_damage[damage_mask & damage_is_positive] += np.abs(damage[damage_mask & damage_is_positive])
            self.total_healing[damage_mask & ~damage_is_positive] += np.abs(damage[damage_mask & ~damage_is_positive])

        self.update_next_hp_check_timestamp(current_timestamp, damage_mask)

        return damage_mask

    def remove_proposal_damage(self, current_timestamp: int, proposal: Proposal):
        if not proposal.is_active or proposal.damage_amounts is None:
            return

        damage_mask = proposal.get_damage_mask()
        if not np.any(damage_mask):
            return

        initial_health = self.hypothetical_health.copy()
        self.hypothetical_health[damage_mask] += proposal.damage_amounts[damage_mask]

        health_change = self.hypothetical_health - initial_health

        if proposal.damage > 0:
            recovery_mask = damage_mask & (health_change > 0)
            if np.any(recovery_mask):
                self.total_recovery[recovery_mask] += np.abs(health_change[recovery_mask])
                self.recovery_time[recovery_mask] = current_timestamp

        self.update_next_hp_check_timestamp(current_timestamp, damage_mask & (health_change != 0))
        proposal.clear_damage_effect()

    def finalize_proposal_damage(self, proposal: Proposal):
        if not proposal.is_active or proposal.damage_amounts is None:
            return

        damage_mask = proposal.get_damage_mask()
        if not np.any(damage_mask):
            return

        self.health[damage_mask] -= proposal.damage_amounts[damage_mask]
        self.cropped_health = np.clip(self.health, 0, 100)

    ## ---
    ## Actor's reaction section
    ## ---

    def check_hp_and_calculate_reaction(
        self, scenario: Scenario, dual_governance: DualGovernance, proposals: List[Proposal]
    ):
        mask = self.next_hp_check_timestamp <= dual_governance.time_manager.get_current_timestamp()
        # get reactions based on HP
        reactions = self.get_reactions_based_on_hp(mask)

        # correct reactions for specific situations and actortypes
        self.correct_reactions(scenario, dual_governance, proposals, reactions, mask)

        # calculate stETH and wstETH changes based on reactions
        stETH_amounts, wstETH_amounts = self.calculate_lock_amount(
            scenario, dual_governance, proposals, reactions, mask
        )

        return reactions, stETH_amounts, wstETH_amounts

    def get_reactions_based_on_hp(self, mask: np.ndarray):
        reactions = np.zeros(self.amount, dtype=np.uint8)
        reactions[:] = ActorReaction.NoReaction.value
        reactions[(self.health > 0) & (self.hypothetical_health > 0) & mask] = ActorReaction.Unlock.value
        reactions[(self.health > 0) & (self.hypothetical_health <= 0) & mask] = ActorReaction.Lock.value
        reactions[(self.health <= 0) & (self.hypothetical_health > 0) & mask] = ActorReaction.Unlock.value
        reactions[(self.health <= 0) & (self.hypothetical_health <= 0) & mask] = ActorReaction.Quit.value
        return reactions

    def correct_reactions(
        self,
        scenario: Scenario,
        dual_governance: DualGovernance,
        proposals: List[Proposal],
        reactions: np.ndarray,
        mask: np.ndarray,
    ):
        self.correct_reactions_HonestActor(scenario, dual_governance, proposals, reactions, mask)
        self.correct_reactions_SingleDefender(scenario, dual_governance, proposals, reactions, mask)
        self.correct_reactions_CoordinatedAttacker(scenario, dual_governance, proposals, reactions, mask)
        self.remove_unnecessary_reactions(scenario, dual_governance, proposals, reactions, mask)

    def remove_unnecessary_reactions(
        self,
        scenario: Scenario,
        dual_governance: DualGovernance,
        proposals: List[Proposal],
        reactions: np.ndarray,
        mask: np.ndarray,
    ):
        already_unlocked_mask = mask * (self.stETH_locked == 0) & (self.wstETH_locked == 0) * (
            reactions == ActorReaction.Unlock.value
        )
        reactions[already_unlocked_mask] = ActorReaction.NoAction.value
        already_locked_mask = (
            mask * ((self.stETH_locked > 0) | (self.wstETH_locked > 0)) * (reactions == ActorReaction.Lock.value)
        )
        reactions[already_locked_mask] = ActorReaction.NoAction.value
        if dual_governance.get_current_state() == State.RageQuit:
            mask1 = mask * ((reactions == ActorReaction.Unlock.value) + (reactions == ActorReaction.Quit.value))
            reactions[mask1] = ActorReaction.NoAction.value

    def update_next_hp_check_timestamp(self, current_timestamp: int, mask: np.ndarray = None):
        self.next_hp_check_timestamp[mask] = current_timestamp + generate_reaction_delay_vector(
            self.reaction_time[mask]
        )

    def quit(self, mask: np.ndarray):
        ## TODO: implement
        self.did_quit[mask] = True
        pass

    ## ---
    ## Lock/unlock actor's logic
    ## ---

    def calculate_lock_amount(
        self,
        scenario: Scenario,
        dual_governance: DualGovernance,
        proposals: List[Proposal],
        reactions: np.ndarray,
        mask: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        stETH_amounts = np.zeros_like(self.stETH)
        wstETH_amounts = np.zeros_like(self.wstETH)

        mask1 = mask * (reactions == ActorReaction.Lock.value)
        stETH_amounts[mask1] = self.stETH[mask1]
        wstETH_amounts[mask1] = self.wstETH[mask1]

        mask2 = mask * ((reactions == ActorReaction.Unlock.value) + (reactions == ActorReaction.Quit.value))
        stETH_amounts[mask2] = -self.stETH_locked[mask2]
        wstETH_amounts[mask2] = -self.wstETH_locked[mask2]

        return stETH_amounts, wstETH_amounts

    ## ---
    ## Honest actors implementation
    ## ---

    def correct_reactions_HonestActor(
        self,
        scenario: Scenario,
        dual_governance: DualGovernance,
        proposals: List[Proposal],
        reactions: np.ndarray,
        mask: np.ndarray,
    ):
        return

    ## ---
    ## Defenders actors implementation
    ## ---
    def correct_reactions_SingleDefender(
        self,
        scenario: Scenario,
        dual_governance: DualGovernance,
        proposals: List[Proposal],
        reactions: np.ndarray,
        mask: np.ndarray,
    ):
        mask1 = mask * (self.actor_type == ActorType.SingleDefender.value)
        if not np.any(mask1):
            return

        if not proposals:
            return
        timelock_proposals = dual_governance.timelock.proposals
        negative_types = {ProposalType.Negative, ProposalType.Danger, ProposalType.Hack}

        all_negative_proposals_canceled = all(
            timelock_proposals._is_proposal_marked_cancelled(proposal.id)
            for proposal in proposals
            if proposal.proposal_type in negative_types
        )

        if all_negative_proposals_canceled:
            locked_mask = mask1 & ((self.stETH_locked > 0) | (self.wstETH_locked > 0))
            reactions[locked_mask] = ActorReaction.Unlock.value

        else:
            unlocked_mask = mask1 & (self.stETH_locked == 0) & (self.wstETH_locked == 0)
            reactions[unlocked_mask] = ActorReaction.Lock.value

    ## ---
    ## Attackers actors implementation
    ## ---

    def correct_reactions_CoordinatedAttacker(
        self,
        scenario: Scenario,
        dual_governance: DualGovernance,
        proposals: List[Proposal],
        reactions: np.ndarray,
        mask: np.ndarray,
    ):
        mask1 = mask * (self.actor_type == ActorType.CoordinatedAttacker.value)
        if not np.any(mask1):
            return

        if not proposals:
            return

        timelock_proposals = dual_governance.timelock.proposals
        proposal_status = dual_governance.timelock.get_proposal_status
        positive_types = {ProposalType.Positive, ProposalType.NoImpact, ProposalType.Random}

        positive_proposals_pending = any(
            not timelock_proposals._is_proposal_marked_cancelled(p.id)
            and proposal_status(p.id) is not ProposalStatus.Executed
            for p in proposals
            if p.proposal_type in positive_types
        )

        if positive_proposals_pending:
            unlocked_mask = mask1 & (self.stETH_locked == 0) & (self.wstETH_locked == 0)
            reactions[unlocked_mask] = ActorReaction.Lock.value
        elif scenario == Scenario.VetoSignallingLoop:
            locked_mask = mask1 & ((self.stETH_locked > 0) | (self.wstETH_locked > 0))
            reactions[locked_mask] = ActorReaction.Unlock.value

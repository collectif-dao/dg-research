import logging
from argparse import ArgumentError
from typing import List, Tuple

import numpy as np

from model.actors.errors import NotEnoughActorStETHBalance, NotEnoughActorWstETHBalance
from model.actors.utils import update_actor_health
from model.types.actors import ActorType
from model.types.proposal_type import ProposalType
from model.types.proposals import Proposal, ProposalSubType
from model.types.scenario import Scenario
from model.utils.proposals import get_first_proposal_timestamp
from model.utils.reactions import generate_reaction_delay_vector
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
        self.initial_health = np.copy(self.health)
        self.total_damage = np.zeros_like(self.health)
        self.total_recovery = np.zeros_like(self.health)
        self.actor_type = actor_type
        self.reaction_time = reaction_time
        self.governance_participation = governance_participation

        self.reaction_delay = np.zeros(shape=self.amount, dtype=np.int64)
        self.recovery_time = np.zeros_like(self.reaction_delay)
        self.last_locked_tx_timestamp = np.zeros_like(self.reaction_delay)

        empty_entity = self.entity == ""
        self.entity[empty_entity] = "Other"

        empty_address = self.address == ""
        self.address[empty_address] = [generate_address() for _ in range(np.sum(empty_address))]

    def simulation_copy(self):
        pass

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

        self.wstETH[mask] -= wstETH_amounts[mask]
        self.wstETH_locked[mask] += wstETH_amounts[mask]

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

        self.wstETH[mask] += np.abs(wstETH_amounts[mask])
        self.wstETH_locked[mask] -= np.abs(wstETH_amounts[mask])

    def rebalance_to_stETH(
        self, stETH_amounts: np.ndarray, wstETH_amounts: np.ndarray, current_timestamp: int, mask: np.ndarray
    ):
        if np.any(
            (self.stETH_locked[mask] + self.wstETH_locked[mask])
            < (np.abs(stETH_amounts[mask]) + np.abs(wstETH_amounts[mask]))
        ):
            raise NotEnoughActorStETHBalance

        self.last_locked_tx_timestamp[mask] = current_timestamp

        self.stETH[mask] += np.abs(stETH_amounts[mask]) + np.abs(wstETH_amounts[mask])
        self.stETH_locked[mask] -= np.abs(stETH_amounts[mask])
        self.wstETH_locked[mask] -= np.abs(wstETH_amounts[mask])

    def update_actor_health_vector(self, current_timestamp: int, damage: np.ndarray, mask: np.ndarray = None):
        if mask is None:
            mask = np.repeat(True, self.amount)

        initial_health = self.health.view()

        mask1 = mask * (damage > 0) * ((self.health - damage) < 0)
        damage[mask1] = self.health[mask1]

        mask2 = mask * (damage > 0)
        self.total_damage[mask2] += damage[mask2]
        self.health[mask2] -= damage[mask2]

        mask3 = mask * (damage < 0) * ((self.health + np.abs(damage)) > 100)
        damage[mask3] = -(100 - self.health[mask3])

        mask4 = mask * (damage < 0) * (self.total_damage > 0)
        self.total_recovery[mask4] += np.abs(damage[mask4])
        self.recovery_time[mask4] = current_timestamp

        mask5 = mask * (damage < 0)
        self.health[mask5] += np.abs(damage[mask5])

        self.health[mask] = np.maximum(np.minimum(self.health[mask], 100), 0)
        self.total_recovery[mask] = np.minimum(self.total_recovery[mask], self.total_damage[mask])

        health_changed_mask = self.health != initial_health
        self.update_reaction_delay(health_changed_mask)

    def update_actor_health(self, current_timestamp: int, damage: np.ndarray, mask: np.ndarray = None):
        if mask is None:
            mask = np.repeat(True, self.amount)

        health_changed_mask = update_actor_health(
            self.health, self.total_damage, self.total_recovery, self.recovery_time, damage, current_timestamp, mask
        )

        self.update_reaction_delay(health_changed_mask)

    def simulate_proposal_effect(self, proposal: Proposal, mask: np.ndarray = None):
        if len(proposal.attack_targets) == 0:
            affected_actors_mask = np.repeat(True, self.amount)
        else:
            affected_actors_mask = np.isin(self.address, list(proposal.attack_targets))

        if mask is not None:
            affected_actors_mask *= mask

        match proposal.sub_type:
            case ProposalSubType.NoEffect:
                affected_actors_mask = np.repeat(False, self.amount)
            case ProposalSubType.FundsStealing:
                affected_actors_mask *= self.entity != "Contract"
            case ProposalSubType.Hack:
                affected_actors_mask *= self.entity == "Contract"

        self.hypothetical_stETH[affected_actors_mask] = 0
        self.hypothetical_wstETH[affected_actors_mask] = 0

    def apply_proposal_damage(
        self, current_timestamp: int, proposal: Proposal, is_damage: bool, mask: np.ndarray = None
    ):
        if mask is None:
            mask = np.repeat(True, self.amount)

        damage = np.repeat(proposal.damage, self.amount)

        for label, label_damage in proposal.effects.effects.items():
            if label_damage != 0:
                damage[self.label == label] = label_damage

        damage[np.logical_not(mask)] = 0

        self.update_actor_health(current_timestamp, damage if is_damage else -damage, mask)

    def update_reaction_delay(self, mask: np.ndarray = None):
        if mask is None:
            self.reaction_delay = generate_reaction_delay_vector(self.reaction_time)
        else:
            self.reaction_delay[mask] = generate_reaction_delay_vector(self.reaction_time[mask])

    def after_simulate_proposal_effect(self, mask: np.ndarray = None):
        if mask is None:
            mask = np.repeat(True, self.amount)

        mask1 = mask * (self.hypothetical_stETH < self.initial_stETH) + (self.hypothetical_wstETH < self.initial_wstETH)
        self.health[mask1] = 0

        total_initial_balance = self.initial_stETH + self.initial_wstETH
        total_hypothetical_balance = self.hypothetical_stETH + self.hypothetical_wstETH
        total_balance_increase = total_hypothetical_balance - total_initial_balance

        mask2 = mask * np.logical_not(mask1) * (total_initial_balance > 0) * (total_balance_increase > 0)

        multiplier = 1 + (total_balance_increase[mask2] / total_initial_balance[mask2])
        multiplier = np.minimum(multiplier, 2)

        multiplier_real = multiplier.real.astype(np.float64)

        self.health = self.health.astype(np.int32)
        self.health[mask2] = (self.health[mask2] * multiplier_real).astype(np.int32)

    def attack_honest_actors(self, proposal: Proposal, stETH_gain: int, wstETH_gain: int, mask: np.ndarray = None):
        if mask is None:
            mask = np.repeat(True, self.amount)
        self.hypothetical_stETH[mask] = self.stETH + stETH_gain
        self.hypothetical_wstETH[mask] = self.wstETH + wstETH_gain

    def calculate_lock_amount(
        self, scenario: Scenario, dual_governance: DualGovernance, proposals: List[Proposal]
    ) -> Tuple[np.ndarray, np.ndarray]:
        stETH_amounts = np.zeros_like(self.stETH)
        wstETH_amounts = np.zeros_like(self.wstETH)

        self.calculate_lock_amount_HonestActor(scenario, dual_governance, proposals, stETH_amounts, wstETH_amounts)
        self.calculate_lock_amount_SingleDefender(scenario, dual_governance, proposals, stETH_amounts, wstETH_amounts)
        self.calculate_lock_amount_CoordinatedAttacker(
            scenario, dual_governance, proposals, stETH_amounts, wstETH_amounts
        )

        return stETH_amounts, wstETH_amounts

    def calculate_lock_amount_HonestActor(
        self,
        scenario: Scenario,
        dual_governance: DualGovernance,
        proposals: List[Proposal],
        stETH_amounts: np.ndarray,
        wstETH_amounts: np.ndarray,
    ):
        mask = self.actor_type == ActorType.HonestActor.value

        if np.sum(mask) < 1:
            return

        mask1 = mask * (self.health <= 0) * (self.total_damage > 0)

        self.calculate_lock_into_escrow_HonestActor(dual_governance, stETH_amounts, wstETH_amounts, mask1)

        mask2 = (
            mask
            * (self.health > 0)
            * (self.total_damage > 0)
            * (self.total_recovery > 0)
            * ((self.stETH_locked > 0) + (self.wstETH_locked > 0))
            * (self.recovery_time > 0)
        )

        self.calculate_unlock_from_escrow_HonestActor(dual_governance, stETH_amounts, wstETH_amounts, mask2)

    def calculate_lock_into_escrow_HonestActor(
        self,
        dual_governance: DualGovernance,
        stETH_amounts: np.ndarray,
        wstETH_amounts: np.ndarray,
        mask: np.ndarray = None,
    ):
        if mask is None:
            mask = np.repeat(True, self.amount)

        first_proposal_timestamp = get_first_proposal_timestamp(dual_governance.timelock.proposals)
        current_timestamp = dual_governance.time_manager.get_current_timestamp()

        mask1 = mask & ((first_proposal_timestamp + self.reaction_delay) <= current_timestamp)

        stETH_amounts[mask1] = self.stETH[mask1]
        wstETH_amounts[mask1] = self.wstETH[mask1]

    def calculate_unlock_from_escrow_HonestActor(
        self,
        dual_governance: DualGovernance,
        stETH_amounts: np.ndarray,
        wstETH_amounts: np.ndarray,
        mask: np.ndarray = None,
    ):
        if dual_governance.get_current_state() == State.RageQuit:
            return

        if mask is None:
            mask = np.repeat(True, self.amount)

        mask1 = mask * (
            (self.recovery_time + self.reaction_delay) <= dual_governance.time_manager.get_current_timestamp()
        )

        stETH_amounts[mask1] = -self.stETH_locked[mask1]
        wstETH_amounts[mask1] = -self.wstETH_locked[mask1]

    def calculate_lock_amount_SingleDefender(
        self,
        scenario: Scenario,
        dual_governance: DualGovernance,
        proposals: List[Proposal],
        stETH_amounts: np.ndarray,
        wstETH_amounts: np.ndarray,
    ):
        mask = self.actor_type == ActorType.SingleDefender.value
        if np.sum(mask) < 1:
            return

        if len(proposals) > 0:
            all_negative_proposals_canceled = all(
                dual_governance.timelock.proposals._is_proposal_marked_cancelled(proposal.id)
                for proposal in proposals
                if proposal.proposal_type in [ProposalType.Negative, ProposalType.Danger, ProposalType.Hack]
            )
            if all_negative_proposals_canceled:
                mask1 = mask * ((self.stETH_locked > 0) + (self.wstETH_locked > 0))
                self.calculate_unlock_from_escrow_HonestActor(dual_governance, stETH_amounts, wstETH_amounts, mask1)
            else:
                mask1 = mask * (self.stETH_locked == 0) * (self.wstETH_locked == 0)
                self.calculate_lock_into_escrow_HonestActor(dual_governance, stETH_amounts, wstETH_amounts, mask1)

    def calculate_lock_amount_CoordinatedAttacker(
        self,
        scenario: Scenario,
        dual_governance: DualGovernance,
        proposals: List[Proposal],
        stETH_amounts: np.ndarray,
        wstETH_amounts: np.ndarray,
    ):
        if scenario != Scenario.VetoSignallingLoop:
            return

        mask = self.actor_type == ActorType.CoordinatedAttacker.value

        if np.sum(mask) == 0:
            return

        if len(proposals) > 0:
            positive_proposals_pending = any(
                (not dual_governance.timelock.proposals._is_proposal_marked_cancelled(proposal.id))
                and (dual_governance.timelock.get_proposal_status(proposal.id) is not ProposalStatus.Executed)
                for proposal in proposals
                if proposal.proposal_type in [ProposalType.Positive, ProposalType.NoImpact, ProposalType.Random]
            )

            if positive_proposals_pending:
                mask1 = mask * (self.stETH_locked == 0) * (self.wstETH_locked == 0)
                self.calculate_lock_into_escrow_HonestActor(dual_governance, stETH_amounts, wstETH_amounts, mask1)
            else:
                mask1 = mask * ((self.stETH_locked > 0) + (self.wstETH_locked > 0))
                self.calculate_unlock_from_escrow_HonestActor(dual_governance, stETH_amounts, wstETH_amounts, mask1)

    def reset_proposal_effect(self):
        self.hypothetical_stETH = self.initial_stETH
        self.hypothetical_wstETH = self.initial_wstETH

    def after_reset_proposal_effect(self):
        mask = (self.hypothetical_stETH == self.initial_stETH) * (self.hypothetical_wstETH == self.initial_wstETH)
        self.health[mask] = self.initial_health

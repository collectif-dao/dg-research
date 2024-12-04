from typing import List, Set

import numpy as np

from model.actors.actors import Actors
from model.types.actors import ActorReaction, ActorType
from model.types.proposal_type import ProposalSubType
from model.types.proposals import Proposal, get_proposal_by_id
from model.types.scenario import Scenario
from specs.dual_governance import DualGovernance
from specs.time_manager import TimeManager


# Behaviors
def check_hp_and_calculate_reaction(params, substep, state_history, prev_state):
    actors: Actors = prev_state["actors"]
    dual_governance: DualGovernance = prev_state["dual_governance"]
    proposals: List[Proposal] = prev_state["proposals"]
    scenario: Scenario = prev_state["scenario"]

    reactions, stETH_amounts, wstETH_amounts = actors.check_hp_and_calculate_reaction(
        scenario, dual_governance, proposals
    )

    return {"agent_delta_staked": [actors.address, stETH_amounts, wstETH_amounts], "actor_reactions": reactions}


# Mechanisms
def react(params, substep, state_history, prev_state, policy_input):
    actors: Actors = prev_state["actors"]
    dual_governance: DualGovernance = prev_state["dual_governance"]
    reactions: np.ndarray = policy_input["actor_reactions"]
    delta_staked_by_agent: List[np.ndarray, np.ndarray, np.ndarray] = policy_input["agent_delta_staked"]
    _, stETH_amounts, wstETH_amounts = delta_staked_by_agent

    mask1 = ((stETH_amounts > 0) | (wstETH_amounts > 0)) & (reactions == ActorReaction.Lock.value)
    actors.lock_to_escrow(stETH_amounts, wstETH_amounts, dual_governance.time_manager.get_current_timestamp(), mask1)

    mask2 = (stETH_amounts < 0) & (wstETH_amounts < 0) & (reactions == ActorReaction.Unlock.value)
    actors.rebalance_to_stETH(
        stETH_amounts, wstETH_amounts, dual_governance.time_manager.get_current_timestamp(), mask2
    )

    mask3 = (
        np.logical_not(mask2) & ((stETH_amounts < 0) | (wstETH_amounts < 0)) & (reactions == ActorReaction.Unlock.value)
    )
    actors.unlock_from_escrow(
        stETH_amounts, wstETH_amounts, dual_governance.time_manager.get_current_timestamp(), mask3
    )

    # mask_reacted = reactions != ActorReaction.NoReaction.value
    # actors.update_next_hp_check_timestamp(dual_governance.time_manager.get_current_timestamp(), mask_reacted)

    mask_quitting = reactions == ActorReaction.Quit.value
    actors.quit(mask_quitting)

    return ("actors", actors)


## ---
## proposals creation effects
## ---


def actor_submit_proposals(params, substep, state_history, prev_state, policy_input):
    proposals: List[Proposal] = policy_input["proposal_create"]
    actors: Actors = prev_state["actors"]
    attackers: Set[str] = prev_state["attackers"]
    scenario: Scenario = prev_state["scenario"]
    dual_governance: DualGovernance = prev_state["dual_governance"]

    actors = actor_update_health(dual_governance, scenario, proposals, actors, attackers)

    return "actors", actors


def actor_update_health(
    dual_governance: DualGovernance,
    scenario: Scenario,
    proposals: List[Proposal],
    actors: Actors,
    attackers: Set[str],
):
    for proposal in proposals:
        if scenario in [Scenario.HappyPath, Scenario.VetoSignallingLoop, Scenario.ConstantVetoSignallingLoop]:
            mask = (actors.actor_type == ActorType.HonestActor.value) * (actors.entity != "Contract") + np.isin(
                actors.actor_type, [ActorType.SingleDefender.value, ActorType.CoordinatedDefender.value]
            )

            actors.simulate_proposal_effect(proposal, mask)
            actors.apply_proposal_damage(dual_governance.time_manager.get_current_timestamp(), proposal, mask)

            ## Update reaction delay for attackers in veto signalling loop attacks
            mask2 = (scenario in [Scenario.VetoSignallingLoop, Scenario.ConstantVetoSignallingLoop]) * np.isin(
                actors.address, list(attackers)
            )
            actors.update_next_hp_check_timestamp(dual_governance.time_manager.get_current_timestamp(), mask2)

        elif scenario in (Scenario.SingleAttack, Scenario.CoordinatedAttack):
            victims_mask = proposal.get_victims_mask(actors, include_contracts=True)

            attackers_mask = np.zeros(actors.amount, dtype=bool)

            if scenario == Scenario.CoordinatedAttack:
                attackers_mask = np.isin(actors.address, list(attackers))
            elif scenario == Scenario.SingleAttack:
                if proposal.proposer in attackers:
                    attackers_mask = actors.address == proposal.proposer

            if np.any(victims_mask & attackers_mask):
                print("WARNING: Found overlap between victims and attackers!")
                print("Fixing by removing overlapping actors from victims...")
                victims_mask &= ~attackers_mask

            actors.simulate_proposal_effect(
                proposal=proposal,
                victims_mask=victims_mask,
                attackers_mask=attackers_mask,
            )

            damage_mask = (actors.actor_type == ActorType.HonestActor.value) * (actors.entity != "Contract") + np.isin(
                actors.actor_type, [ActorType.SingleDefender.value, ActorType.CoordinatedDefender.value]
            )

            actors.apply_proposal_damage(dual_governance.time_manager.get_current_timestamp(), proposal, damage_mask)

    return actors


## ---
## proposals cancellation effects
## ---


def actor_cancel_proposals(params, substep, state_history, prev_state, policy_input):
    cancel_proposal_ids = policy_input["cancel_all_pending_proposals"]
    if not cancel_proposal_ids:
        return ("actors", prev_state["actors"])

    actors: Actors = prev_state["actors"]
    proposals: List[Proposal] = prev_state["proposals"]
    time_manager: TimeManager = prev_state["time_manager"]

    for proposal_id in cancel_proposal_ids:
        proposal = get_proposal_by_id(proposals, proposal_id)
        if proposal is None:
            continue

        if proposal.is_active:
            actors.remove_proposal_damage(time_manager.get_current_timestamp(), proposal)

            if proposal.sub_type in [ProposalSubType.FundsStealing, ProposalSubType.Bribing]:
                actors.reset_proposal_effect(proposal)

    return ("actors", actors)


## ---
## proposals execution effects
## ---


def actor_execute_proposals(params, substep, state_history, prev_state, policy_input):
    actors: Actors = prev_state["actors"]
    proposals_to_execute: List[Proposal] = policy_input["proposals_to_execute"]

    for dg_proposal in proposals_to_execute:
        proposal = get_proposal_by_id(prev_state["proposals"], dg_proposal.id)
        if proposal is not None:
            actors.finalize_proposal_damage(proposal)

            if proposal.sub_type in [ProposalSubType.FundsStealing, ProposalSubType.Bribing]:
                actors.finalize_proposal_effect(proposal)

    return ("actors", actors)

from typing import List, Set

import numpy as np

from model.actors.actors import Actors
from model.types.actors import ActorType
from model.types.proposal_type import ProposalSubType
from model.types.proposals import Proposal, get_proposal_by_id
from model.types.scenario import Scenario
from specs.dual_governance import DualGovernance
from specs.lido import Lido
from specs.time_manager import TimeManager


# Behaviors
def lock_or_unlock_stETH(params, substep, state_history, prev_state):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    actors: Actors = prev_state["actors"]
    proposals: List[Proposal] = prev_state["proposals"]
    scenario: Scenario = prev_state["scenario"]

    stETH_amounts, wstETH_amounts = actors.calculate_lock_amount(scenario, dual_governance, proposals)
    # if np.sum(stETH_amounts) > 0 or np.sum(wstETH_amounts) > 0:
    #     print(f"stETH_amounts is {np.sum(stETH_amounts)}")
    #     print(f"wstETH_amounts is {np.sum(wstETH_amounts)}")

    return {"agent_delta_staked": [actors.address, stETH_amounts, wstETH_amounts]}


# Mechanisms
def actor_lock_or_unlock_in_escrow(params, substep, state_history, prev_state, policy_input):
    delta_staked_by_agent: List[np.ndarray, np.ndarray, np.ndarray] = policy_input["agent_delta_staked"]
    actors: Actors = prev_state["actors"]
    dual_governance: DualGovernance = prev_state["dual_governance"]

    _, stETH_amounts, wstETH_amounts = delta_staked_by_agent

    mask1 = (stETH_amounts > 0) + (wstETH_amounts > 0)
    # if np.sum(mask1) > 0:
    #     print(f"mask 1 in actor_lock_or_unlock_in_escrow is {np.sum(mask1)}")
    actors.lock_to_escrow(stETH_amounts, wstETH_amounts, dual_governance.time_manager.get_current_timestamp(), mask1)

    mask2 = (stETH_amounts < 0) * (wstETH_amounts < 0)
    actors.rebalance_to_stETH(
        stETH_amounts, wstETH_amounts, dual_governance.time_manager.get_current_timestamp(), mask2
    )

    mask3 = np.logical_not(mask2) * ((stETH_amounts < 0) + (wstETH_amounts < 0))
    actors.unlock_from_escrow(
        stETH_amounts, wstETH_amounts, dual_governance.time_manager.get_current_timestamp(), mask3
    )

    return ("actors", actors)


## ---
## proposals creation effects
## ---


def actor_react_on_proposal(params, substep, state_history, prev_state, policy_input):
    proposals: List[Proposal | None] = policy_input["proposal_create"]
    actors: Actors = prev_state["actors"]
    lido: Lido = prev_state["lido"]
    attackers: Set[str] = prev_state["attackers"]
    dual_governance: DualGovernance = prev_state["dual_governance"]
    time_manager: TimeManager = prev_state["time_manager"]
    scenario: Scenario = prev_state["scenario"]

    if proposals is not None:
        actors = actor_update_health(scenario, proposals, dual_governance, lido, actors, attackers, time_manager)

    return "actors", actors


def actor_update_health(
        scenario: Scenario,
        proposals: List[Proposal | None],
        dual_governance: DualGovernance,
        lido: Lido,
        actors: Actors,
        attackers: Set[str],
        time_manager: TimeManager,
):
    # print(f"actor_update_health proposals is {proposals}")
    for proposal in proposals:
        if proposal is not None:
            last_canceled_proposal = dual_governance.timelock.proposals.state.last_canceled_proposal_id

            if proposal.id > last_canceled_proposal:
                if scenario in [Scenario.HappyPath, Scenario.VetoSignallingLoop]:
                    mask = (actors.actor_type == ActorType.HonestActor.value) * (actors.entity != "Contract") + np.isin(
                        actors.actor_type, [ActorType.SingleDefender.value, ActorType.CoordinatedDefender.value]
                    )

                    actors.simulate_proposal_effect(proposal, mask)
                    actors.apply_proposal_damage(time_manager.get_current_timestamp(), proposal, True, mask)

                elif scenario in (Scenario.SingleAttack, Scenario.CoordinatedAttack):
                    total_stETH_gains, total_wstETH_gains = calculate_attack_gains(
                        proposal, dual_governance, lido, actors, attackers
                    )
                    # print(f"total_stETH_gains is {total_stETH_gains}")
                    # print(f"total_wstETH_gains is {total_wstETH_gains}")

                    if scenario == Scenario.SingleAttack:
                        num_attackers = 1
                    elif scenario == Scenario.CoordinatedAttack:
                        num_attackers = len(attackers)
                    else:
                        num_attackers = 0

                    mask1 = (actors.actor_type == ActorType.HonestActor.value) * (
                            actors.entity != "Contract"
                    ) + np.isin(
                        actors.actor_type, [ActorType.SingleDefender.value, ActorType.CoordinatedDefender.value]
                    )

                    actors.simulate_proposal_effect(proposal, mask1)
                    actors.apply_proposal_damage(time_manager.get_current_timestamp(), proposal, True, mask1)
                    actors.after_simulate_proposal_effect(mask1)

                    mask2 = (scenario == Scenario.CoordinatedAttack) * np.isin(actors.address, list(attackers)) + (
                            scenario == Scenario.SingleAttack
                    ) * (proposal.proposer in attackers) * (actors.address == proposal.proposer)

                    if np.sum(mask2) > 0:
                        stETH_gain_per_attacker = total_stETH_gains / num_attackers
                        wstETH_gain_per_attacker = total_wstETH_gains / num_attackers
                        print(
                            "stealing from honest actors ",
                            stETH_gain_per_attacker,
                            " stETH and ",
                            wstETH_gain_per_attacker,
                            " wstETH",
                        )
                        actors.attack_honest_actors(proposal, stETH_gain_per_attacker, wstETH_gain_per_attacker, mask2)
                        actors.after_simulate_proposal_effect(mask2)

    return actors


def calculate_attack_gains(
        proposal: Proposal | None,
        dual_governance: DualGovernance,
        lido: Lido,
        actors: Actors,
        coordinated_attackers: Set[str],
) -> (int, int):
    n_attackers = np.sum(
        np.isin(actors.actor_type, [ActorType.SingleAttacker.value, ActorType.CoordinatedAttacker.value])
    )
    if n_attackers < 1:
        print("no attackers in the system")
        return 0, 0

    condition1 = np.isin(
        actors.actor_type,
        [ActorType.HonestActor.value, ActorType.SingleDefender.value, ActorType.CoordinatedDefender.value],
    )
    condition2 = actors.entity != "Contract"
    condition3 = np.isin(actors.address, list(proposal.attack_targets))
    mask = condition1 * condition2
    if len(proposal.attack_targets) != 0:
        mask *= condition3

    total_stETH_funds = np.sum(actors.stETH[mask])
    total_wstETH_funds = np.sum(actors.wstETH[mask])

    match proposal.sub_type:
        case ProposalSubType.NoEffect:
            return 0, 0

        case ProposalSubType.FundsStealing:
            print(
                len(coordinated_attackers),
                " attackers in the system that is going to steal ",
                total_stETH_funds,
                " stETH and ",
                total_wstETH_funds,
                " wstETH",
            )
            return total_stETH_funds, total_wstETH_funds

        case ProposalSubType.Bribing:
            return 0, 0


## ---
## proposals cancellation effects
## ---


def actor_reset_proposal_reaction(params, substep, state_history, prev_state, policy_input):
    cancel_proposal_ids = policy_input["cancel_all_pending_proposals"]
    actors: Actors = prev_state["actors"]
    proposals: List[Proposal] = prev_state["proposals"]
    time_manager: TimeManager = prev_state["time_manager"]

    actors = actor_recover_health(cancel_proposal_ids, actors, proposals, time_manager)
    actors = actor_reset_proposal_effect(cancel_proposal_ids, actors, proposals)

    return ("actors", actors)


def actor_recover_health(cancel_proposal_ids, actors: Actors, proposals: List[Proposal], time_manager: TimeManager):
    if len(cancel_proposal_ids) != 0:
        for proposal_id in cancel_proposal_ids:
            proposal = get_proposal_by_id(proposals, proposal_id)
            if proposal.damage != 0:
                mask = (actors.actor_type == ActorType.HonestActor.value) * (actors.entity != "Contract")
                actors.apply_proposal_damage(time_manager.get_current_timestamp(), proposal, False, mask=mask)

    return actors


def actor_reset_proposal_effect(cancel_proposal_ids, actors: Actors, proposals: List[Proposal]):
    reset: bool = False

    if len(cancel_proposal_ids) != 0:
        print("actor_reset_proposal_effect", cancel_proposal_ids)
        for proposal_id in cancel_proposal_ids:
            if reset:
                break

            proposal = get_proposal_by_id(proposals, proposal_id)
            if proposal.sub_type in [ProposalSubType.FundsStealing, ProposalSubType.Bribing]:
                actors.reset_proposal_effect()
                actors.after_reset_proposal_effect()

                reset = True

    return actors

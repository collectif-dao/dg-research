from typing import Dict, List, Set

from model.actors.actor import BaseActor
from model.types.actors import ActorType
from model.types.escrow import ActorLockAmounts
from model.types.proposal_type import ProposalSubType
from model.types.proposals import Proposal, get_proposal_by_id
from model.types.scenario import Scenario
from specs.dual_governance import DualGovernance
from specs.lido import Lido
from specs.time_manager import TimeManager


# Behaviors
def lock_or_unlock_stETH(params, substep, state_history, prev_state):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    actors: List[BaseActor] = prev_state["actors"]
    proposals: List[Proposal] = prev_state["proposals"]
    scenario: Scenario = prev_state["scenario"]
    staked: Dict[str, ActorLockAmounts] = dict()

    for actor in actors:
        stETH_amount, wstETH_amount = actor.calculate_lock_amount(scenario, dual_governance, proposals)

        if stETH_amount is None:
            stETH_amount = 0

        if wstETH_amount is None:
            wstETH_amount = 0

        staked[actor.address] = ActorLockAmounts(stETH_amount=stETH_amount, wstETH_amount=wstETH_amount)

    return {"agent_delta_staked": staked}


# Mechanisms
def actor_lock_or_unlock_in_escrow(params, substep, state_history, prev_state, policy_input):
    delta_staked_by_agent: Dict[str, ActorLockAmounts] = policy_input["agent_delta_staked"]
    actors: List[BaseActor] = prev_state["actors"]
    dual_governance: DualGovernance = prev_state["dual_governance"]

    for actor in actors:
        if actor.address in delta_staked_by_agent:
            amounts = delta_staked_by_agent[actor.address]

            if amounts.stETH_amount > 0 or amounts.wstETH_amount > 0:
                actor.lock_to_escrow(amounts, dual_governance.time_manager)
                continue

            if amounts.stETH_amount < 0 and amounts.wstETH_amount < 0:
                actor.rebalance_to_stETH(amounts, dual_governance.time_manager)
                continue

            if amounts.stETH_amount < 0 or amounts.wstETH_amount < 0:
                actor.unlock_from_escrow(amounts, dual_governance.time_manager)
                continue

    return ("actors", actors)


## ---
## proposals creation effects
## ---


def actor_react_on_proposal(params, substep, state_history, prev_state, policy_input):
    proposal = policy_input["proposal_create"]
    actors: List[BaseActor] = prev_state["actors"]
    lido: Lido = prev_state["lido"]
    attackers: Set[str] = prev_state["attackers"]
    dual_governance: DualGovernance = prev_state["dual_governance"]
    time_manager: TimeManager = prev_state["time_manager"]
    scenario: Scenario = prev_state["scenario"]

    actors = actor_update_health(scenario, proposal, dual_governance, lido, actors, attackers, time_manager)

    return ("actors", actors)


def actor_update_health(
    scenario: Scenario,
    proposal: Proposal | None,
    dual_governance: DualGovernance,
    lido: Lido,
    actors: List[BaseActor],
    attackers: Set[str],
    time_manager: TimeManager,
):
    if proposal is not None:
        if proposal.damage != 0:
            last_canceled_proposal = dual_governance.timelock.proposals.state.last_canceled_proposal_id

            if proposal.id > last_canceled_proposal:
                if scenario in [Scenario.HappyPath, Scenario.VetoSignallingLoop]:
                    for actor in actors:
                        actor.simulate_proposal_effect(proposal)
                        actor.update_actor_health(time_manager, proposal.damage)

                elif scenario in (Scenario.SingleAttack, Scenario.CoordinatedAttack):
                    total_stETH_gains, total_wstETH_gains = calculate_attack_gains(
                        proposal, dual_governance, lido, actors, attackers
                    )

                    if scenario == Scenario.SingleAttack:
                        num_attackers = 1
                    elif scenario == Scenario.CoordinatedAttack:
                        num_attackers = len(attackers)

                    if num_attackers > 0:
                        stETH_gain_per_attacker = total_stETH_gains / num_attackers
                        wstETH_gain_per_attacker = total_wstETH_gains / num_attackers

                    for actor in actors:
                        if (
                            actor.actor_type == ActorType.HonestActor
                            and actor.entity != "Contract"
                            or (actor.actor_type in [ActorType.SingleDefender, ActorType.CoordinatedDefender])
                        ):
                            actor.simulate_proposal_effect(proposal)
                            actor.update_actor_health(time_manager, proposal.damage)
                            actor.after_simulate_proposal_effect()

                        if (scenario == Scenario.CoordinatedAttack and actor.address in attackers) or (
                            scenario == Scenario.SingleAttack
                            and proposal.proposer in attackers
                            and actor.address == proposal.proposer
                        ):
                            print(
                                "stealing from honest actors ",
                                stETH_gain_per_attacker,
                                " stETH and ",
                                wstETH_gain_per_attacker,
                                " wstETH",
                            )
                            actor.attack_honest_actors(proposal, stETH_gain_per_attacker, wstETH_gain_per_attacker)
                            actor.after_simulate_proposal_effect()

    return actors


def calculate_attack_gains(
    proposal: Proposal | None,
    dual_governance: DualGovernance,
    lido: Lido,
    actors: List[BaseActor],
    coordinated_attackers: Set[str],
):
    if not any(actor.actor_type in [ActorType.SingleAttacker, ActorType.CoordinatedAttacker] for actor in actors):
        print("no attackers in the system")
        return 0, 0

    total_stETH_funds: int = 0
    total_wstETH_funds: int = 0

    for actor in actors:
        if (
            actor.actor_type in [ActorType.HonestActor, ActorType.CoordinatedDefender, ActorType.SingleDefender]
            and actor.entity != "Contract"
        ):
            if len(proposal.attack_targets) != 0 and actor.address in proposal.attack_targets:
                total_stETH_funds += actor.st_eth_balance
                total_wstETH_funds += actor.wstETH_balance
            elif len(proposal.attack_targets) == 0:
                total_stETH_funds += actor.st_eth_balance
                total_wstETH_funds += actor.wstETH_balance

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
    actors: List[BaseActor] = prev_state["actors"]
    proposals: List[Proposal] = prev_state["proposals"]
    time_manager: TimeManager = prev_state["time_manager"]

    actors = actor_recover_health(cancel_proposal_ids, actors, proposals, time_manager)
    actors = actor_reset_proposal_effect(cancel_proposal_ids, actors, proposals)

    return ("actors", actors)


def actor_recover_health(
    cancel_proposal_ids, actors: List[BaseActor], proposals: List[Proposal], time_manager: TimeManager
):
    if len(cancel_proposal_ids) != 0:
        for id in cancel_proposal_ids:
            proposal = get_proposal_by_id(proposals, id)
            if proposal.damage != 0:
                for actor in actors:
                    if actor.actor_type == ActorType.HonestActor and actor.entity != "Contract":
                        actor.update_actor_health(time_manager, -proposal.damage)

    return actors


def actor_reset_proposal_effect(cancel_proposal_ids, actors: List[BaseActor], proposals: List[Proposal]):
    reset: bool = False

    if len(cancel_proposal_ids) != 0:
        print("actor_reset_proposal_effect", cancel_proposal_ids)
        for id in cancel_proposal_ids:
            if reset:
                break

            proposal = get_proposal_by_id(proposals, id)
            if proposal.sub_type in [ProposalSubType.FundsStealing, ProposalSubType.Bribing]:
                for actor in actors:
                    actor.reset_proposal_effect()
                    actor.after_reset_proposal_effect()

                reset = True

    return actors

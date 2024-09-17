from typing import List

import pandas as pd
from pandas import DataFrame

from model.actors.actor import BaseActor
from model.types.actors import ActorType
from model.types.reaction_time import ReactionTime
from specs.dual_governance.proposals import ProposalStatus
from specs.utils import ether_base, percent_base


def postprocessing(df: DataFrame):
    dg_ds = df.dual_governance
    time_manager_ds = df.time_manager
    timesteps = df.timestep
    actors: List[BaseActor] = df.actors
    proposals = df.proposals

    proposals_submitted_count = dg_ds.map(
        lambda s: sum([1 for proposal in s.timelock.proposals.state.proposals if proposal.submittedAt.value != 0])
    )

    proposals_executed_count = dg_ds.map(
        lambda s: sum([1 for proposal in s.timelock.proposals.state.proposals if proposal.executedAt.value != 0])
    )

    proposals_canceled_count = dg_ds.map(
        lambda s: sum(
            [
                1
                for proposal in s.timelock.proposals.state.proposals
                if proposal.status != ProposalStatus.Executed
                and proposal.id <= s.timelock.proposals.state.last_canceled_proposal_id
            ]
        )
    )

    total_quick_actors_reaction_time = actors.map(
        lambda actors: sum([1 for actor in actors if actor.reaction_time == ReactionTime.Quick])
    )

    total_wstETH_quick_actors = actors.map(
        lambda actors: sum(
            [actor.initial_wstETH_balance for actor in actors if actor.reaction_time == ReactionTime.Quick]
        )
    )

    total_stETH_quick_actors = actors.map(
        lambda actors: sum(
            [actor.initial_st_eth_balance for actor in actors if actor.reaction_time == ReactionTime.Quick]
        )
    )

    total_slow_actors_reaction_time = actors.map(
        lambda actors: sum([1 for actor in actors if actor.reaction_time == ReactionTime.Slow])
    )

    total_wstETH_slow_actors = actors.map(
        lambda actors: sum(
            [actor.initial_wstETH_balance for actor in actors if actor.reaction_time == ReactionTime.Slow]
        )
    )

    total_stETH_slow_actors = actors.map(
        lambda actors: sum(
            [actor.initial_st_eth_balance for actor in actors if actor.reaction_time == ReactionTime.Slow]
        )
    )

    total_normal_actors_reaction_time = actors.map(
        lambda actors: sum([1 for actor in actors if actor.reaction_time == ReactionTime.Normal])
    )

    total_wstETH_normal_actors = actors.map(
        lambda actors: sum(
            [actor.initial_wstETH_balance for actor in actors if actor.reaction_time == ReactionTime.Normal]
        )
    )

    total_stETH_normal_actors = actors.map(
        lambda actors: sum(
            [actor.initial_st_eth_balance for actor in actors if actor.reaction_time == ReactionTime.Normal]
        )
    )

    total_non_reactive_actors_reaction_time = actors.map(
        lambda actors: sum([1 for actor in actors if actor.reaction_time == ReactionTime.NoReaction])
    )

    total_wstETH_non_reactive_actors = actors.map(
        lambda actors: sum(
            [actor.initial_wstETH_balance for actor in actors if actor.reaction_time == ReactionTime.NoReaction]
        )
    )

    total_stETH_non_reactive_actors = actors.map(
        lambda actors: sum(
            [actor.initial_st_eth_balance for actor in actors if actor.reaction_time == ReactionTime.NoReaction]
        )
    )

    total_quick_actors_funds = (total_stETH_quick_actors + total_wstETH_quick_actors) / ether_base
    total_normal_actors_funds = (total_stETH_normal_actors + total_wstETH_normal_actors) / ether_base
    total_slow_actors_funds = (total_stETH_slow_actors + total_wstETH_slow_actors) / ether_base
    total_non_reactive_actors_funds = (total_stETH_non_reactive_actors + total_wstETH_non_reactive_actors) / ether_base

    total_actors_health = actors.map(lambda actors: sum([actor.health for actor in actors]))

    total_contracts_health = actors.map(
        lambda actors: sum([actor.health for actor in actors if actor.entity == "Contract"])
    )
    total_honest_actors_health = actors.map(
        lambda actors: sum([actor.health for actor in actors if actor.actor_type == ActorType.HonestActor])
    )
    total_attackers_actors_health = actors.map(
        lambda actors: sum(
            [
                actor.health
                for actor in actors
                if actor.actor_type in [ActorType.CoordinatedAttacker, ActorType.SingleAttacker]
            ]
        )
    )

    total_attackers_stETH_hypothetical_balance = actors.map(
        lambda actors: sum(
            [
                actor.hypothetical_stETH_balance
                for actor in actors
                if actor.actor_type in [ActorType.CoordinatedAttacker, ActorType.SingleAttacker]
            ]
        )
    )

    total_attackers_wstETH_hypothetical_balance = actors.map(
        lambda actors: sum(
            [
                actor.hypothetical_wstETH_balance
                for actor in actors
                if actor.actor_type in [ActorType.CoordinatedAttacker, ActorType.SingleAttacker]
            ]
        )
    )

    total_honest_actors_hypothetical_balance = actors.map(
        lambda actors: sum(
            [
                actor.hypothetical_stETH_balance
                for actor in actors
                if actor.actor_type in [ActorType.HonestActor, ActorType.SingleDefender, ActorType.CoordinatedDefender]
            ]
        )
    )

    total_actors_damaged = actors.map(lambda actors: sum([actor.total_damage for actor in actors]))
    total_actors_recovery = actors.map(lambda actors: sum([actor.total_recovery for actor in actors]))

    total_stETH_balance = actors.map(lambda actors: sum([actor.st_eth_balance / ether_base for actor in actors]))
    total_stETH_locked = actors.map(lambda actors: sum([actor.st_eth_locked / ether_base for actor in actors]))

    total_wstETH_balance = actors.map(lambda actors: sum([actor.wstETH_balance / ether_base for actor in actors]))
    total_wstETH_locked = actors.map(lambda actors: sum([actor.wstETH_locked / ether_base for actor in actors]))

    current_time = time_manager_ds.map(lambda s: s.current_time)

    dg_state = dg_ds.map(lambda s: s.state.state)

    rage_quit_support = dg_ds.map(lambda s: s.state.signalling_escrow.get_rage_quit_support() / percent_base)

    total_stETH_good_actors = actors.map(
        lambda actors: sum([1 for actor in actors if actor.actor_type == ActorType.HonestActor])
    )

    total_attackers = actors.map(
        lambda actors: sum(
            [1 for actor in actors if actor.actor_type in {ActorType.SingleAttacker, ActorType.CoordinatedAttacker}]
        )
    )

    total_defenders = actors.map(
        lambda actors: sum(
            [1 for actor in actors if actor.actor_type in {ActorType.SingleDefender, ActorType.CoordinatedDefender}]
        )
    )

    total_wstETH_honest_actors = actors.map(
        lambda actors: sum(
            [actor.initial_wstETH_balance for actor in actors if actor.actor_type == ActorType.HonestActor]
        )
    )

    total_stETH_honest_actors = actors.map(
        lambda actors: sum(
            [actor.initial_st_eth_balance for actor in actors if actor.actor_type == ActorType.HonestActor]
        )
    )

    total_wstETH_attackers_actors = actors.map(
        lambda actors: sum(
            [
                actor.initial_wstETH_balance
                for actor in actors
                if actor.actor_type in {ActorType.SingleAttacker, ActorType.CoordinatedAttacker}
            ]
        )
    )

    total_stETH_attackers_actors = actors.map(
        lambda actors: sum(
            [
                actor.initial_st_eth_balance
                for actor in actors
                if actor.actor_type in {ActorType.SingleAttacker, ActorType.CoordinatedAttacker}
            ]
        )
    )

    total_wstETH_defenders_actors = actors.map(
        lambda actors: sum(
            [
                actor.initial_wstETH_balance
                for actor in actors
                if actor.actor_type in {ActorType.SingleDefender, ActorType.CoordinatedDefender}
            ]
        )
    )

    total_stETH_defenders_actors = actors.map(
        lambda actors: sum(
            [
                actor.initial_st_eth_balance
                for actor in actors
                if actor.actor_type in {ActorType.SingleDefender, ActorType.CoordinatedDefender}
            ]
        )
    )

    total_honest_actors_funds = (total_wstETH_honest_actors + total_stETH_honest_actors) / ether_base
    total_attackers_actors_funds = (total_wstETH_attackers_actors + total_stETH_attackers_actors) / ether_base
    total_defenders_actors_funds = (total_wstETH_defenders_actors + total_stETH_defenders_actors) / ether_base

    total_damage_of_proposals = proposals.map(lambda proposals: sum([proposal.damage for proposal in proposals]))
    total_number_of_proposals = proposals.map(lambda proposals: sum([1 for proposal in proposals if proposal.id > 0]))
    average_damage_per_proposal = total_damage_of_proposals.combine(
        total_number_of_proposals, lambda x, y: x / y if y != 0 else 0
    )

    # Create an analysis dataset
    data = pd.DataFrame(
        {
            "dg_state": dg_state,
            "current_time": current_time,
            ## Actors health
            "total_actors_health": total_actors_health,
            "total_contracts_health": total_contracts_health,
            "total_honest_actors_health": total_honest_actors_health,
            "total_attackers_actors_health": total_attackers_actors_health,
            "total_actors_damaged": total_actors_damaged,
            "total_actors_recovery": total_actors_recovery,
            ## Funds in the systems (locks, attack effects, initial balances)
            "total_stETH_balance": total_stETH_balance,
            "total_stETH_locked": total_stETH_locked,
            "total_wstETH_balance": total_wstETH_balance,
            "total_wstETH_locked": total_wstETH_locked,
            "total_attackers_stETH_hypothetical_balance": total_attackers_stETH_hypothetical_balance,
            "total_attackers_wstETH_hypothetical_balance": total_attackers_wstETH_hypothetical_balance,
            "total_honest_actors_hypothetical_balance": total_honest_actors_hypothetical_balance,
            "rage_quit_support": rage_quit_support,
            ## Proposals effects on the system
            "total_damage_of_proposals": total_damage_of_proposals,
            "total_number_of_proposals": total_number_of_proposals,
            "average_damage_per_proposal": average_damage_per_proposal,
            ## Proposals flow within the system
            "proposals_submitted_count": proposals_submitted_count,
            "proposals_executed_count": proposals_executed_count,
            "proposals_canceled_count": proposals_canceled_count,
            ## actors distribution based on reaction delay
            "total_quick_actors_reaction_time": total_quick_actors_reaction_time,
            "total_normal_actors_reaction_time": total_normal_actors_reaction_time,
            "total_slow_actors_reaction_time": total_slow_actors_reaction_time,
            "total_non_reactive_actors_reaction_time": total_non_reactive_actors_reaction_time,
            ## funds distribution of actors based on reaction delay
            "total_wstETH_quick_actors": total_wstETH_quick_actors,
            "total_wstETH_normal_actors": total_wstETH_normal_actors,
            "total_wstETH_slow_actors": total_wstETH_slow_actors,
            "total_wstETH_non_reactive_actors": total_wstETH_non_reactive_actors,
            "total_stETH_quick_actors": total_stETH_quick_actors,
            "total_stETH_normal_actors": total_stETH_normal_actors,
            "total_stETH_slow_actors": total_stETH_slow_actors,
            "total_stETH_non_reactive_actors": total_stETH_non_reactive_actors,
            ## total funds distribution of actors based on reaction delay
            "total_quick_actors_funds": total_quick_actors_funds,
            "total_normal_actors_funds": total_normal_actors_funds,
            "total_slow_actors_funds": total_slow_actors_funds,
            "total_non_reactive_actors_funds": total_non_reactive_actors_funds,
            ## Distribution of actors based on behavior
            "total_stETH_good_actors": total_stETH_good_actors,
            "total_attackers": total_attackers,
            "total_defenders": total_defenders,
            # Total funds distribution based on actor's behavior
            "total_honest_actors_funds": total_honest_actors_funds,
            "total_attackers_actors_funds": total_attackers_actors_funds,
            "total_defenders_actors_funds": total_defenders_actors_funds,
            # simulation parameters
            "timestep": timesteps,
            # "run": df.run,
            "simulation": df.simulation + 1,
        }
    )

    return data

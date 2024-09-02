import csv
from typing import Any, List, Set, Tuple

from model.actors.actor import BaseActor
from model.actors.token_holders.stETH_holder_actor import StETHHolderActor
from model.parts.actors import actor_update_health
from model.types.actors import ActorType
from model.types.governance_participation import GovernanceParticipation
from model.types.proposal_type import ProposalGeneration, ProposalType
from model.types.proposals import Proposal, ProposalSubType
from model.types.reaction_time import ModeledReactions, ReactionTime
from model.types.scenario import Scenario
from model.utils.actors import (
    determine_actor_health,
    determine_actor_types,
)
from model.utils.reactions import determine_governance_participation, determine_reaction_time
from model.utils.seed import initialize_seed
from specs.dual_governance import DualGovernance
from specs.dual_governance.proposals import ExecutorCall
from specs.lido import Lido
from specs.time_manager import TimeManager
from specs.types.address import Address
from specs.utils import ether_base


def generate_initial_state(
    scenario: Scenario = Scenario.HappyPath,
    reactions: ModeledReactions = ModeledReactions.Normal,
    proposal_types: ProposalType = ProposalType.NoImpact,
    proposal_subtypes: ProposalSubType = ProposalSubType.NoEffect,
    proposal_generation: ProposalGeneration = ProposalGeneration.Random,
    initial_proposals: List[Proposal] = [],
    max_actors: int = 0,
    attackers: Set[str] = set(),
    seed: int | str = None,
) -> Any:
    initialize_seed(seed)

    proposals: List[Proposal] = []
    non_initialized_proposals: List[Proposal] = []
    actors, attackers = generate_actors(scenario, reactions, max_actors, attackers)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)

    dual_governance = DualGovernance()
    dual_governance.initialize(Address.test_escrow_address, time_manager, lido)

    for actor in actors:
        if actor.st_eth_balance > 0:
            buffered_ether = lido.get_buffered_ether()
            lido._mint_shares(actor.address, actor.st_eth_balance)
            lido.set_buffered_ether(buffered_ether + actor.st_eth_balance)

        if actor.wstETH_balance > 0:
            buffered_ether = lido.get_buffered_ether()
            lido._mint_shares(actor.address, actor.wstETH_balance)
            lido.set_buffered_ether(buffered_ether + actor.wstETH_balance)
            lido.approve(actor.address, Address.wstETH, actor.wstETH_balance)

            lido.wrap(actor.address, actor.wstETH_balance)

    if len(initial_proposals) > 0:
        proposals, non_initialized_proposals = generate_initial_proposals(
            initial_proposals,
            dual_governance,
            scenario,
            len(attackers),
        )

    print(proposals)
    print(non_initialized_proposals)
    is_active_attack = False

    if len(proposals) > 0:
        for proposal in proposals:
            actors = actor_update_health(scenario, proposal, dual_governance, lido, actors, attackers)

            if proposal.proposal_type in (ProposalType.Danger, ProposalType.Hack, ProposalType.Negative):
                is_active_attack = True

    print(attackers)

    return {
        "actors": actors,
        "lido": lido,
        "dual_governance": dual_governance,
        "proposals": proposals,
        "non_initialized_proposals": non_initialized_proposals,
        "time_manager": time_manager,
        "scenario": scenario,
        "attackers": attackers,
        "proposal_types": proposal_types,
        "proposal_subtypes": proposal_subtypes,
        "is_active_attack": is_active_attack,
        "proposal_generation": proposal_generation,
        "seed": seed,
    }


def generate_actors(
    scenario: Scenario, reactions: ModeledReactions, max_actors: int, attackers: Set[str]
) -> Tuple[List[BaseActor], Set[str]]:
    initial_actors = []

    with open("data/stETH_token_distribution.csv", mode="r") as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=",")
        line_count = 0

        for row in csv_reader:
            if max_actors > 0 and line_count > max_actors:
                break

            if line_count == 0:
                line_count += 1
                continue

            created_actor = create_actor(
                attackers,
                scenario,
                reactions,
                line_count,
                row["address"],
                0,
                int(float(row["stETH"]) * ether_base),
                int(float(row["wstETH"]) * ether_base),
                row["type"],
            )

            initial_actors.append(created_actor)

            if created_actor.address not in attackers:
                match scenario:
                    case Scenario.CoordinatedAttack:
                        if created_actor.actor_type == ActorType.CoordinatedAttacker:
                            attackers.add(created_actor.address)
                    case Scenario.SingleAttack:
                        if created_actor.actor_type == ActorType.SingleAttacker:
                            attackers.add(created_actor.address)
                    case Scenario.SmartContractHack:
                        if created_actor.actor_type == ActorType.Hacker:
                            attackers.add(created_actor.address)

            line_count += 1

    return initial_actors, attackers


def create_actor(
    attackers: Set[str],
    scenario: Scenario,
    reactions: ModeledReactions,
    id: int,
    address: str,
    ldo: int,
    stETH: int,
    wstETH: int,
    type: str,
):
    created_actor = determine_actor_types(scenario, address, attackers)
    health = determine_actor_health(scenario)

    if type == "Contract":
        created_actor = StETHHolderActor()
        reaction_time = ReactionTime.NoReaction
        participation = GovernanceParticipation.NoParticipation
    else:
        reaction_time = determine_reaction_time(reactions)
        participation = determine_governance_participation(reactions)

    if created_actor.actor_type in {ActorType.SingleAttacker, ActorType.CoordinatedAttacker}:
        reaction_time = ReactionTime.Quick
        participation = GovernanceParticipation.Full

    created_actor.initialize(id, type, address, health, ldo, stETH, wstETH, reaction_time, participation)

    return created_actor


def generate_initial_proposals(
    initial_proposals: List[Proposal],
    dual_governance: DualGovernance,
    scenario: Scenario,
    total_attackers: int = 0,
) -> Tuple[List[Proposal], List[Proposal]]:
    if not dual_governance.state.is_proposals_creation_allowed():
        return [], initial_proposals

    if scenario in [Scenario.SingleAttack, Scenario.CoordinatedAttack] and total_attackers <= 0:
        return [], initial_proposals

    proposals: List[Proposal] = []
    non_initialized_proposals: List[Proposal] = []

    for proposal in initial_proposals:
        new_proposal_id = (
            dual_governance.timelock.proposals.count() + dual_governance.timelock.proposals.proposal_id_offset
        )

        proposal.id = new_proposal_id

        if proposal.timestep == 0:
            dual_governance.submit_proposal("", [ExecutorCall("", "", [])])
            proposals.append(proposal)
        else:
            non_initialized_proposals.append(proposal)

    return proposals, non_initialized_proposals

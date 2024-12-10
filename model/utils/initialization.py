import csv
from datetime import datetime
from typing import Any, Callable, List, Set, Tuple, Union

import numpy as np

from model.actors.actors import Actors
from model.parts.actors import actor_update_health
from model.types.actors import ActorType
from model.types.governance_participation import GovernanceParticipation
from model.types.proposal_type import ProposalGeneration, ProposalType
from model.types.proposals import Proposal, ProposalSubType
from model.types.reaction_time import ModeledReactions, ReactionTime
from model.types.scenario import Scenario
from model.utils.proposals_queue import ProposalQueueManager
from model.utils.reactions import determine_governance_participation_vector, determine_reaction_time_vector
from model.utils.seed import initialize_seed
from specs.dual_governance import DualGovernance
from specs.dual_governance.proposals import ExecutorCall
from specs.lido import Lido
from specs.time_manager import TimeManager
from specs.types.address import Address
from specs.types.timestamp import Timestamp
from specs.utils import ether_base


def generate_initial_state(
    scenario: Scenario = Scenario.HappyPath,
    reactions: ModeledReactions = ModeledReactions.Normal,
    proposal_types: ProposalType = None,
    proposal_subtypes: ProposalSubType = None,
    proposal_generation: ProposalGeneration = ProposalGeneration.Random,
    initial_proposals: List[Proposal] = [],
    max_actors: int = 0,
    attackers: Set[str] = set(),
    defenders: Set[str] = set(),
    seed: int | str = None,
    simulation_starting_time: datetime = datetime.min,
    first_rage_quit_support: int = None,
    second_rage_quit_support: int = None,
    institutional_threshold: int = 0,
    labeled_addresses: Union[dict[str, str], Callable] = dict(),
    attacker_funds: int = 0,
    determining_factor: int = 0,
    save_data_enabled: bool = True,
) -> Any:
    initialize_seed(seed)

    proposals: List[Proposal] = []
    non_initialized_proposals: List[Proposal] = []
    actors = generate_actors(
        scenario,
        reactions,
        max_actors,
        attackers,
        defenders,
        labeled_addresses,
        institutional_threshold,
        attacker_funds,
        determining_factor,
    )

    time_manager = TimeManager(current_time=simulation_starting_time, simulation_start_time=simulation_starting_time)

    if simulation_starting_time == datetime.min:
        time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)

    filtered_params = {
        "first_seal_rage_quit_support": first_rage_quit_support,
        "second_seal_rage_quit_support": second_rage_quit_support,
    }
    filtered_params = {k: v for k, v in filtered_params.items() if v is not None}

    dual_governance = DualGovernance()
    dual_governance.initialize(
        Address.test_escrow_address, time_manager, lido, "", "", Timestamp(0), Timestamp(0), **filtered_params
    )

    for i in range(actors.amount):
        if actors.stETH[i] > 0:
            buffered_ether = lido.get_buffered_ether()
            lido._mint_shares(actors.address[i], actors.stETH[i])
            lido.set_buffered_ether(buffered_ether + actors.stETH[i])

        if actors.wstETH[i] > 0:
            buffered_ether = lido.get_buffered_ether()
            lido._mint_shares(actors.address[i], actors.wstETH[i])
            lido.set_buffered_ether(buffered_ether + actors.wstETH[i])
            lido.approve(actors.address[i], Address.wstETH, actors.wstETH[i])
            lido.wrap(actors.address[i], actors.wstETH[i])

    proposals_queue: ProposalQueueManager = ProposalQueueManager()

    if len(initial_proposals) > 0:
        proposals, non_initialized_proposals = generate_initial_proposals(
            initial_proposals,
            dual_governance,
            scenario,
            proposals_queue,
            len(attackers),
        )

    is_active_attack = False

    if len(proposals) > 0:
        ## TODO: add proposal_effects here
        actors = actor_update_health(dual_governance, scenario, proposals, actors, attackers)

        for proposal in proposals:
            if proposal.proposal_type in (ProposalType.Danger, ProposalType.Hack, ProposalType.Negative):
                is_active_attack = True

    attackers_actors = actors.address[
        (actors.actor_type == ActorType.SingleAttacker.value)
        + (actors.actor_type == ActorType.CoordinatedAttacker.value)
    ]
    defenders_actors = actors.address[
        (actors.actor_type == ActorType.SingleDefender.value)
        + (actors.actor_type == ActorType.CoordinatedDefender.value)
    ]

    return {
        "actors": actors,
        "lido": lido,
        "dual_governance": dual_governance,
        "proposals": proposals,
        "non_initialized_proposals": non_initialized_proposals,
        "time_manager": time_manager,
        "scenario": scenario,
        "attackers": attackers_actors,
        "defenders": defenders_actors,
        "proposal_types": proposal_types,
        "proposal_subtypes": proposal_subtypes,
        "is_active_attack": is_active_attack,
        "proposal_generation": proposal_generation,
        "seed": seed,
        "simulation_starting_time": time_manager.get_current_timestamp(),
        "first_seal_rage_quit_support": dual_governance.state.config.first_seal_rage_quit_support,
        "second_seal_rage_quit_support": dual_governance.state.config.second_seal_rage_quit_support,
        "attacker_funds": attacker_funds,
        "proposals_queue": proposals_queue,
        "timestep_data": {},
        "determining_factor": determining_factor,
        "save_data_enabled": save_data_enabled,
    }


def parse_token_amount(token_amount_str):
    if "." not in token_amount_str:
        return int(token_amount_str) * ether_base
    parts = token_amount_str.split(".")
    pad = "".join("0" for _ in range(int(np.log10(ether_base) - len(parts[1]))))
    return int(parts[0] + parts[1] + pad)


def generate_actors(
    scenario: Scenario,
    reactions: ModeledReactions,
    max_actors: int,
    attackers: Set[str],
    defenders: Set[str],
    labeled_addresses: Union[dict[str, str], Callable] = dict(),
    institutional_threshold: int = 0,
    attacker_funds: int = 0,
    determining_factor: int = 0,
) -> Actors:
    from model.utils.seed import get_rng

    rng = get_rng()
    actor_addresses = []
    actor_ldo = []
    actor_stETH = []
    actor_wstETH = []
    actor_typestr = []
    actor_label = []

    with open("data/stETH token distribution  - stETH+wstETH holders.csv", mode="r") as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=",")
        for line_id, row in enumerate(csv_reader):
            if 0 < max_actors < line_id + 1:
                break
            actor_addresses.append(row["address"])
            actor_ldo.append(0)
            actor_stETH.append(parse_token_amount(row["stETH"]))
            actor_wstETH.append(parse_token_amount(row["wstETH"]))
            actor_typestr.append(row["type"])
            actor_label.append(row["label"])

    actor_addresses = np.array(actor_addresses)
    actor_ldo = np.array(actor_ldo)
    actor_stETH = np.array(actor_stETH)
    actor_wstETH = np.array(actor_wstETH)
    actor_typestr = np.array(actor_typestr)
    actor_label = np.array(actor_label)
    actor_types = np.zeros(len(actor_label), dtype="uint8") + ActorType.HonestActor.value
    actor_health = np.array(rng.normal(loc=50, scale=20, size=len(actor_label)), dtype="int32")
    actor_health = np.maximum(np.minimum(actor_health, 100), 1)

    attacker_type = {
        Scenario.SingleAttack: ActorType.SingleAttacker.value,
        Scenario.CoordinatedAttack: ActorType.CoordinatedAttacker.value,
        Scenario.VetoSignallingLoop: ActorType.CoordinatedAttacker.value,
        Scenario.ConstantVetoSignallingLoop: ActorType.CoordinatedAttacker.value,
        Scenario.RageQuitLoop: ActorType.CoordinatedAttacker.value,
    }.get(scenario, ActorType.HonestActor.value)

    if attacker_funds > 0:
        if attackers:
            attacker_indices = np.where(np.isin(actor_addresses, list(attackers)))[0]
            actor_types[attacker_indices] = attacker_type

            total_funds = actor_stETH[attacker_indices] + actor_wstETH[attacker_indices]
            funds_needed = attacker_funds * ether_base - total_funds
            actor_stETH[attacker_indices] += np.maximum(funds_needed, 0)
        else:
            actor_addresses = np.append(actor_addresses, "0xAttacker")
            actor_stETH = np.append(actor_stETH, attacker_funds * ether_base)
            actor_wstETH = np.append(actor_wstETH, 0)
            actor_typestr = np.append(actor_typestr, "Attacker")
            actor_label = np.append(actor_label, "Attacker")
            actor_types = np.append(actor_types, attacker_type)
            actor_health = np.append(actor_health, 100)
            actor_ldo = np.append(actor_ldo, 0)
    else:
        random_attackers = rng.normal(loc=0, scale=1, size=len(actor_addresses)) >= 3
        actor_types[random_attackers] = attacker_type

    defender_mask = np.isin(actor_addresses, list(defenders))
    actor_types[defender_mask] = ActorType.SingleDefender.value

    actor_reaction_time = determine_reaction_time_vector(len(actor_addresses), reactions)
    actor_participation = determine_governance_participation_vector(len(actor_addresses), reactions)
    if institutional_threshold != 0:
        institutional_mask = actor_stETH + actor_wstETH >= institutional_threshold * ether_base
        actor_reaction_time[institutional_mask] = ReactionTime.Slow.value

    attacker_mask = np.isin(actor_addresses, list(attackers))
    abstaining_mask = np.all(
        (np.isin(actor_typestr, ["Contract", "CEX", "Custody"]), ~attacker_mask, ~defender_mask), axis=0
    )
    actor_reaction_time[abstaining_mask] = ReactionTime.NoReaction.value
    actor_participation[abstaining_mask] = GovernanceParticipation.Abstaining.value

    override_mask = np.isin(
        actor_types,
        [
            ActorType.SingleAttacker.value,
            ActorType.CoordinatedAttacker.value,
            ActorType.SingleDefender.value,
            ActorType.CoordinatedDefender.value,
        ],
    )
    actor_reaction_time[override_mask] = ReactionTime.Quick.value
    actor_participation[override_mask] = GovernanceParticipation.Full.value

    if callable(labeled_addresses):
        quick_normal_mask = np.isin(actor_reaction_time, [ReactionTime.Normal.value, ReactionTime.Quick.value])

        actor_label = labeled_addresses(
            existing_labels=actor_label,
            reaction_mask=quick_normal_mask,
            stETH_amounts=actor_stETH,
            wstETH_amounts=actor_wstETH,
            determining_factor=determining_factor,
        )
    else:
        actor_label = np.array(
            [labeled_addresses.get(addr, label) for addr, label in zip(actor_addresses, actor_label)]
        )

    actors = Actors(
        address=actor_addresses,
        ldo=actor_ldo,
        stETH=actor_stETH,
        wstETH=actor_wstETH,
        entity=actor_typestr,
        label=actor_label,
        actor_type=actor_types,
        health=actor_health,
        reaction_time=actor_reaction_time,
        governance_participation=actor_participation,
    )

    return actors


def generate_initial_proposals(
    initial_proposals: List[Proposal],
    dual_governance: DualGovernance,
    scenario: Scenario,
    proposals_queue: ProposalQueueManager,
    total_attackers: int = 0,
) -> Tuple[List[Proposal], List[Proposal]]:
    if not dual_governance.state.is_proposals_creation_allowed():
        return [], initial_proposals

    if (
        scenario
        in [
            Scenario.SingleAttack,
            Scenario.CoordinatedAttack,
            Scenario.VetoSignallingLoop,
            Scenario.ConstantVetoSignallingLoop,
            Scenario.RageQuitLoop,
        ]
        and total_attackers <= 0
    ):
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
            proposals_queue.last_registration_timestep = 0
            proposals.append(proposal)
        else:
            non_initialized_proposals.append(proposal)

    return proposals, non_initialized_proposals

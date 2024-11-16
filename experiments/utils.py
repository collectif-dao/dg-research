import collections.abc
import pickle
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from json_tricks import dumps
from radcad import Backend, Engine, Experiment, Model, Simulation

from model.state_update_blocks import state_update_blocks
from model.sys_params import sys_params
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.reaction_time import ModeledReactions
from model.types.scenario import Scenario
from model.utils.initialization import generate_initial_state
from specs.utils import ether_base, percent_base

collections.Hashable = collections.abc.Hashable


@dataclass
class DualGovernanceParameters:
    first_rage_quit_support: int = None
    second_rage_quit_support: int = None


def get_simulation_hash(initial_state=None, state_update_blocks=None, params=None, timesteps=None):
    initial_state_json = dumps(initial_state)
    initial_state_hash = sha256(initial_state_json.encode("utf-8"))

    state_update_blocks_bytes = pickle.dumps(state_update_blocks)
    params_bytes = pickle.dumps(params)

    combined_bytes = state_update_blocks_bytes + params_bytes
    simulation_hash = sha256(initial_state_hash.digest() + combined_bytes).hexdigest()

    return simulation_hash + "-" + str(timesteps)


def get_batch_hash(simulation_hashes: list[str], timesteps=None):
    combined_hash = "".join(simulation_hashes).encode("utf-8")
    batch_hash = sha256(combined_hash).hexdigest()

    return batch_hash + "-" + str(timesteps)


# noinspection PyDefaultArgument
def setup_simulation(
        timesteps: int,
        monte_carlo_runs: int,
        scenario: Scenario,
        proposal_types: ProposalType,
        proposal_subtypes: ProposalSubType,
        proposals_generation: ProposalGeneration,
        proposals: list[Proposal] = [],
        attackers: set[str] = set(),
        defenders: set[str] = set(),
        seed: int = 0,
        simulation_starting_time: datetime = datetime.min,
        out_dir: str = "",
        dual_governance_params: list[DualGovernanceParameters] = None,
        max_actors: int = 0,
        institutional_threshold: int = 0,
        labeled_addresses: dict[str, str] = dict(),
        save_files: bool = True,
        batch_size: int = 100,
):
    simulations: list[Simulation] = []
    simulation_hashes: list[str] = []

    if dual_governance_params is None:
        dual_governance_params = [DualGovernanceParameters()]

    for run in range(monte_carlo_runs):
        seed_str = seed + run

        for params in dual_governance_params:
            first_rage_quit_support = None
            second_rage_quit_support = None

            if params.first_rage_quit_support is not None:
                first_rage_quit_support = params.first_rage_quit_support * percent_base

            if params.second_rage_quit_support is not None:
                second_rage_quit_support = params.second_rage_quit_support * percent_base

            state = generate_initial_state(
                scenario,
                ModeledReactions.Normal,
                proposal_types,
                proposal_subtypes,
                proposals_generation,
                proposals,
                max_actors,
                attackers,
                defenders,
                seed_str,
                simulation_starting_time,
                first_rage_quit_support=first_rage_quit_support,
                second_rage_quit_support=second_rage_quit_support,
                institutional_threshold=institutional_threshold,
                labeled_addresses=labeled_addresses,
            )

            state_data = construct_state_data(
                actors=state["actors"],
                scenario=state["scenario"],
                proposal_types=state["proposal_types"],
                proposal_subtypes=state["proposal_subtypes"],
                proposal_generation=state["proposal_generation"],
                proposals=state["proposals"],
                non_initialized_proposals=state["non_initialized_proposals"],
                attackers=state["attackers"],
                defenders=state["defenders"],
                seed=state["seed"],
                simulation_starting_time=state["simulation_starting_time"],
                first_seal_rage_quit_support=state["first_seal_rage_quit_support"],
                second_seal_rage_quit_support=state["second_seal_rage_quit_support"],
            )

            simulation_hash = get_simulation_hash(
                initial_state=state_data,
                state_update_blocks=state_update_blocks,
                params=sys_params,
                timesteps=timesteps,
            )

            simulation_hashes.append(simulation_hash)

            state["outpath"] = ""
            state["simulation_hash"] = simulation_hash
            state["n_timesteps"] = timesteps
            model = Model(initial_state=state, params=sys_params, state_update_blocks=state_update_blocks)
            simulation = Simulation(model=model, timesteps=timesteps, runs=1)

            simulations.append(simulation)

    total_simulations = len(simulations)
    batch_count = (total_simulations + batch_size - 1) // batch_size

    skipped_simulations = set()
    for batch_idx in range(batch_count):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, total_simulations)

        batch_simulations = simulations[start_idx:end_idx]
        batch_hash = get_batch_hash(simulation_hashes[start_idx:end_idx], timesteps)

        batch_folder_path = Path(out_dir).joinpath(f"batch_{batch_hash}/")
        common_file = batch_folder_path / "common_data.parquet"
        proposals_file = batch_folder_path / "proposals_data.parquet"
        timestep_file = batch_folder_path / "timestep_data.parquet"

        if batch_folder_path.exists() and all(f.is_file() for f in [common_file, proposals_file, timestep_file]):
            print(f"Skipping batch {batch_hash} as it already exists with required files.")
            skipped_simulations.update(batch_simulations)
            continue

        if save_files:
            batch_folder_path.mkdir(exist_ok=True, parents=True)

        for simulation in batch_simulations:
            simulation.model.initial_state["outpath"] = batch_folder_path
            simulation.model.state["outpath"] = batch_folder_path

    simulations = [sim for sim in simulations if sim not in skipped_simulations]

    experiment = Experiment(simulations)

    experiment.engine = Engine(backend=Backend.MULTIPROCESSING, raise_exceptions=False, drop_substeps=True)

    return experiment, simulation_hashes


def construct_state_data(**kwargs):
    state_data = {}

    for key, value in kwargs.items():
        state_data[key] = value

    return state_data

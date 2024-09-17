import collections
import collections.abc
import pickle
import re
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pandas as pd
from json_tricks import dumps
from radcad import Backend, Engine, Experiment, Model, Simulation

from model.state_update_blocks import state_update_blocks
from model.sys_params import sys_params
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.reaction_time import ModeledReactions
from model.types.scenario import Scenario
from model.utils.initialization import generate_initial_state
from model.utils.postprocessing import postprocessing
from specs.utils import ether_base

collections.Hashable = collections.abc.Hashable


def get_simulation_hash(initial_state=None, state_update_blocks=None, params=None, timesteps=None):
    initial_state_json = dumps(initial_state)
    initial_state_hash = sha256(initial_state_json.encode("utf-8"))

    state_update_blocks_bytes = pickle.dumps(state_update_blocks)
    params_bytes = pickle.dumps(params)

    combined_bytes = state_update_blocks_bytes + params_bytes
    simulation_hash = sha256(initial_state_hash.digest() + combined_bytes).hexdigest()

    return simulation_hash + "-" + str(timesteps)


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
):
    simulations: list[Simulation] = []
    simulation_hashes: list[str] = []

    for run in range(monte_carlo_runs):
        seed_str = seed + run
        state = generate_initial_state(
            scenario,
            ModeledReactions.Normal,
            proposal_types,
            proposal_subtypes,
            proposals_generation,
            proposals,
            0,
            attackers,
            defenders,
            seed_str,
            simulation_starting_time,
        )

        model = Model(initial_state=state, params=sys_params, state_update_blocks=state_update_blocks)
        simulation = Simulation(model=model, timesteps=timesteps, runs=1)

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
        )

        simulation_hash = get_simulation_hash(
            initial_state=state_data,
            state_update_blocks=simulation.model.state_update_blocks,
            params=simulation.model.params,
            timesteps=timesteps,
        )

        simulation_hashes.append(simulation_hash)

        folder_path = out_dir.joinpath(f"{simulation_hash}/")
        results_file = folder_path / "result.pkl"
        actors_file = folder_path / "actors.pkl"

        if folder_path.exists() and results_file.is_file() and actors_file.is_file():
            print(f"Skipping simulation {simulation_hash} as it already exists with required files.")
            continue

        simulations.append(simulation)

    experiment = Experiment(simulations)
    experiment.engine = Engine(backend=Backend.MULTIPROCESSING, processes=5, raise_exceptions=False, drop_substeps=True)

    return experiment, simulation_hashes


def merge_simulation_results(simulation_hashes: str, simulation_name: str, out_dir=None):
    dfs: list = []
    simulation_counter = 0
    simulation_path = out_dir.joinpath(f"{simulation_name}/")

    for simulation_hash in simulation_hashes:
        folder_path = simulation_path.joinpath(f"{simulation_hash}/")
        results_file = folder_path / "result.pkl"

        if not results_file.is_file():
            print(f"Warning: File {results_file} does not exist. Skipping this simulation.")
            continue

        with open(results_file, "rb") as f:
            df = pickle.load(f)

        df["simulation"] = simulation_counter
        dfs.append(df)
        simulation_counter += 1

    combined_df = pd.concat(dfs, ignore_index=True)
    # combined_result_file = simulation_path.joinpath(Path("results.csv"))
    # combined_df.to_csv(combined_result_file, index=False)

    return combined_df


def create_actors_df(simulation_result, out_dir=None):
    if out_dir == None:
        out_dir = Path("")
    result_path = out_dir.joinpath(Path("actors.pkl"))

    value_dict = defaultdict(list)
    value_dict["reaction_delay"] = []

    index: int = simulation_result["timestep"].head(1).index.tolist()[0]

    for actors in simulation_result["actors"]:
        for actor in actors:
            for key, value in vars(actor).items():
                if re.search("eth", key, flags=re.IGNORECASE):
                    value /= ether_base

                value_dict[key].append(value)
            for key in value_dict:
                if (key not in vars(actor)) and (key not in ("seed", "timestep")):
                    value_dict[key].append(None)

            value_dict["seed"].append(simulation_result["seed"][index])
            value_dict["timestep"].append(simulation_result["timestep"][index])

        index += 1

    df = pd.DataFrame(value_dict)
    df.reset_index()

    with open(result_path, "wb") as f:
        pickle.dump(df, f)


def save_combined_actors_simulation_result(simulation_hashes: list[str], simulation_name: str, out_path: Path):
    dfs: list = []
    simulation_counter = 0
    simulation_path = out_path.joinpath(f"{simulation_name}/")

    for hash in simulation_hashes:
        folder_path = simulation_path.joinpath(f"{hash}/")
        actors_file = folder_path / "actors.pkl"

        with open(actors_file, "rb") as f:
            actors_df = pickle.load(f)

        actors_df["simulation"] = simulation_counter
        dfs.append(actors_df)
        simulation_counter += 1

    out_filepath = simulation_path.joinpath(Path("actors.csv"))
    # parquet_filepath = simulation_path.joinpath(Path("actors.parquet"))

    combined_df = pd.concat(dfs, ignore_index=True)
    combined_df.to_csv(out_filepath, index=False)
    # combined_df.to_parquet(parquet_filepath)

    return combined_df


def save_execution_result(experiment, simulation_name, timesteps, out_dir):
    if out_dir == None:
        out_dir = Path("")

    experiment_df = pd.DataFrame(experiment.results)
    simulations = experiment.get_simulations()

    simulation_path = out_dir.joinpath(f"{simulation_name}/")
    simulation_path.mkdir(exist_ok=True)

    for run in range(len(simulations)):
        start_idx = run + (run * timesteps)
        end_idx = start_idx + timesteps + 1

        state_data = construct_state_data(
            actors=simulations[run].model.initial_state["actors"],
            scenario=simulations[run].model.initial_state["scenario"],
            proposal_types=simulations[run].model.initial_state["proposal_types"],
            proposal_subtypes=simulations[run].model.initial_state["proposal_subtypes"],
            proposal_generation=simulations[run].model.initial_state["proposal_generation"],
            proposals=simulations[run].model.initial_state["proposals"],
            non_initialized_proposals=simulations[run].model.initial_state["non_initialized_proposals"],
            attackers=simulations[run].model.initial_state["attackers"],
            defenders=simulations[run].model.initial_state["defenders"],
            seed=simulations[run].model.initial_state["seed"],
            simulation_starting_time=simulations[run].model.initial_state["simulation_starting_time"],
        )

        simulation_hash = get_simulation_hash(
            initial_state=state_data,
            state_update_blocks=experiment.simulations[run].model.state_update_blocks,
            params=experiment.simulations[run].model.params,
            timesteps=experiment.simulations[run].timesteps,
        )

        folder_path = simulation_path.joinpath(f"{simulation_hash}/")
        folder_path.mkdir(exist_ok=True)

        sliced_df = experiment_df.iloc[start_idx:end_idx]
        result_path = folder_path.joinpath("result.pkl")

        with open(result_path, "wb") as f:
            pickle.dump(sliced_df, f)

        create_actors_df(sliced_df, folder_path)


def save_postprocessing_result(dataframe: pd.DataFrame, simulation_name: str, out_path: Path):
    post_processing = postprocessing(dataframe)
    folder_path = out_path.joinpath(f"{simulation_name}")
    result_path = folder_path.joinpath("post_processing.csv")
    # parquet_filepath = folder_path.joinpath("post_processing.parquet")

    post_processing.to_csv(result_path, index=False)
    # post_processing.to_parquet(parquet_filepath)


def construct_state_data(**kwargs):
    state_data = {}

    for key, value in kwargs.items():
        state_data[key] = value

    return state_data

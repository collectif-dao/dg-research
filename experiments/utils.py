import collections.abc
import pickle
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Callable, Union

import numpy as np
import pandas as pd
from json_tricks import dumps
from radcad import Backend, Engine, Experiment, Model, Simulation

from model.state_update_blocks import state_update_blocks
from model.sys_params import CustomDelays, sys_params
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.reaction_time import ModeledReactions
from model.types.scenario import Scenario
from model.utils.initialization import generate_initial_state
from model.utils.postprocessing import postprocessing
from specs.utils import ether_base, percent_base

collections.Hashable = collections.abc.Hashable


@dataclass
class DualGovernanceParameters:
    first_rage_quit_support: int = None
    second_rage_quit_support: int = None
    after_schedule_delay: int = 0
    attacker_funds: int = 0
    determining_factor: int = 0
    custom_delays: CustomDelays = CustomDelays()
    lido_exit_share: int = 0.3
    churn_rate: int = 14
    modeled_reactions: ModeledReactions = ModeledReactions.Normal
    deposit_cap: int = 300_000
    process_deposits: bool = False


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
    labeled_addresses: Union[dict[str, str], Callable] = dict(),
    time_profiling: bool = False,
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
                params.modeled_reactions,
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
                attacker_funds=params.attacker_funds,
                determining_factor=params.determining_factor,
                custom_delays=params.custom_delays,
                lido_exit_share=params.lido_exit_share,
                churn_rate=params.churn_rate,
                process_deposits=params.process_deposits,
            )

            state_custom_delays = state["reaction_delay_generator"].custom_delays

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
                modeled_reactions=state["modeled_reactions"],
                attacker_funds=state["attacker_funds"],
                determining_factor=state["determining_factor"],
                custom_delays=state_custom_delays,
                process_deposits=state["process_deposits"],
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
    batch_simulations = []

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

    drop_substeps = not time_profiling
    experiment.engine = Engine(backend=Backend.MULTIPROCESSING, raise_exceptions=False, drop_substeps=drop_substeps)

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


def iterate_simulation_results(simulation_path: str):
    simulation_counter = 0
    simulation_path = Path(simulation_path)
    simulation_run_paths = filter(lambda p: p.is_dir(), simulation_path.iterdir())

    for simulation_run_path in simulation_run_paths:
        results_file = simulation_run_path.joinpath("result.pkl")
        with open(results_file, "rb") as f:
            run_df = pickle.load(f)
        run_df["simulation"] = simulation_counter
        yield run_df
        simulation_counter += 1


def get_common_columns_to_extract_from_simulation_result():
    return ["first_seal_rage_quit_support", "second_seal_rage_quit_support", "seed", "timestep"]


def extract_dg_state_data(run_df):
    run_df["dg_state"] = run_df.dual_governance.apply(lambda x: x.state.state)
    run_df["dg_state_value"] = run_df["dg_state"].apply(lambda state: state.value)
    run_df["dg_state_name"] = run_df["dg_state"].apply(lambda state: state.name)
    run_df["dg_dynamic_timelock_hours"] = run_df.dual_governance.apply(
        lambda dg: dg.state._calc_dynamic_timelock_duration(
            dg.state.signalling_escrow.get_rage_quit_support()
        ).to_seconds()
        / 60
        / 60
    )

    columns_to_extract = get_common_columns_to_extract_from_simulation_result()
    columns_to_extract += ["dg_state_value", "dg_state_name", "dg_dynamic_timelock_hours"]
    extracted_data = run_df[columns_to_extract].copy()
    return extracted_data


def extract_proposal_data(run_df):
    run_df["last_cancelled_proposal_id"] = run_df["dual_governance"].apply(
        lambda dg: dg.timelock.proposals.state.last_canceled_proposal_id
    )
    cancelled_proposals = set(run_df["last_cancelled_proposal_id"].unique())

    simulation_start = (
        run_df[(run_df["timestep"] == 0)].time_manager.apply(lambda tm: tm.current_time).iloc[0].timestamp()
    )
    proposals_info = run_df.dual_governance.apply(lambda dg: dg.timelock.proposals.state.proposals).iloc[-1]
    proposal_dict = defaultdict(list)
    for proposal in proposals_info:
        proposal_dict["id"].append(proposal.id)
        proposal_dict["status"].append(proposal.status)
        proposal_dict["submittedAt"].append((proposal.submittedAt.to_seconds() - simulation_start) / 3600 / 3)
        proposal_dict["scheduledAt"].append((proposal.scheduledAt.to_seconds() - simulation_start) / 3600 / 3)
        proposal_dict["executedAt"].append((proposal.executedAt.to_seconds() - simulation_start) / 3600 / 3)
    for proposal_id in proposal_dict["id"]:
        if proposal_id in cancelled_proposals:
            row_when_cancelled = np.argmax(run_df["last_cancelled_proposal_id"] == proposal_id)
            timestep_when_cancelled = run_df.iloc[row_when_cancelled].timestep
            proposal_dict["cancelledAt"].append(timestep_when_cancelled)
        else:
            proposal_dict["cancelledAt"].append(None)

    common_data = run_df[get_common_columns_to_extract_from_simulation_result()].drop(columns="timestep")
    for col in common_data:
        proposal_dict[col] = [common_data[col].iloc[0] for _ in range(len(proposal_dict["id"]))]

    proposal_df = pd.DataFrame(proposal_dict).set_index("id")
    return proposal_df


def aggregate_actor_data(actor_df):
    actor_df["total_balance"] = actor_df.st_eth_balance + actor_df.wstETH_balance
    actor_df["total_locked"] = actor_df.st_eth_locked + actor_df.wstETH_locked

    total_initial_balance = actor_df[actor_df["timestep"] == 0]["total_balance"].sum()
    total_actors = len(actor_df[actor_df["timestep"] == 0]["id"].unique())
    actor_df["actor_locked"] = actor_df["total_locked"] > 0
    actor_df_final = (
        actor_df.groupby(get_common_columns_to_extract_from_simulation_result())
        .agg({"total_balance": "sum", "total_locked": "sum", "actor_locked": "sum", "health": "sum"})
        .reset_index()
    )
    initial_system_health = actor_df[actor_df["timestep"] == 0]["health"].sum()
    actor_df_final["total_locked_ratio"] = actor_df_final["total_locked"] / total_initial_balance
    actor_df_final["actor_locked_ratio"] = actor_df_final["actor_locked"] / total_actors
    actor_df_final["system_health_ratio"] = actor_df_final["health"] / initial_system_health
    actor_df_final["system_health"] = actor_df_final["health"]
    actor_df_final.drop(columns=["health"])
    return actor_df_final


def extract_actor_data(run_df):
    common_columns = get_common_columns_to_extract_from_simulation_result()
    run_df_actors = run_df[common_columns + ["actors"]].explode("actors")
    actor_columns = [
        "st_eth_balance",
        "initial_st_eth_balance",
        "st_eth_locked",
        "wstETH_balance",
        "initial_wstETH_balance",
        "wstETH_locked",
        "health",
        "id",
    ]
    for col in actor_columns:
        run_df_actors[col] = run_df_actors.actors.apply(lambda actor: vars(actor)[col])
    actor_df = run_df_actors[common_columns + actor_columns]
    aggregated_actor_df = aggregate_actor_data(actor_df)
    return aggregated_actor_df


def create_actors_df(simulation_result, out_dir=None):
    if out_dir is None:
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
                if (key not in vars(actor)) and (
                    key not in ("seed", "timestep", "first_seal_rage_quit_support", "second_seal_rage_quit_support")
                ):
                    value_dict[key].append(None)

            value_dict["seed"].append(simulation_result["seed"][index])
            value_dict["timestep"].append(simulation_result["timestep"][index])
            value_dict["first_seal_rage_quit_support"].append(simulation_result["first_seal_rage_quit_support"][index])
            value_dict["second_seal_rage_quit_support"].append(
                simulation_result["second_seal_rage_quit_support"][index]
            )

        index += 1

    df = pd.DataFrame(value_dict)
    df.reset_index()

    with open(result_path, "wb") as f:
        pickle.dump(df, f)


def save_combined_actors_simulation_result(simulation_hashes: list[str], simulation_name: str, out_path: Path):
    dfs: list = []
    simulation_counter = 0
    simulation_path = out_path.joinpath(f"{simulation_name}/")

    for hash_str in simulation_hashes:
        folder_path = simulation_path.joinpath(f"{hash_str}/")
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


def save_execution_result(
    experiment, simulation_name, timesteps, out_dir, create_actors_df_flag=True, drop_substeps=True
):
    if out_dir is None:
        out_dir = Path("")
    experiment_df = pd.DataFrame(experiment.results)
    simulations = experiment.get_simulations()

    simulation_path = out_dir.joinpath(f"{simulation_name}/")
    simulation_path.mkdir(exist_ok=True)

    for run in range(len(simulations)):
        if drop_substeps:
            substeps = 1
        else:
            substeps = len(experiment.simulations[run].model.state_update_blocks)
        start_idx = run + (run * timesteps * substeps)
        end_idx = start_idx + timesteps * substeps + 1

        state_custom_delays = simulations[run].model.initial_state["reaction_delay_generator"].custom_delays

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
            first_seal_rage_quit_support=simulations[run].model.initial_state["first_seal_rage_quit_support"],
            second_seal_rage_quit_support=simulations[run].model.initial_state["second_seal_rage_quit_support"],
            modeled_reactions=simulations[run].model.initial_state["modeled_reactions"],
            attacker_funds=simulations[run].model.initial_state["attacker_funds"],
            determining_factor=simulations[run].model.initial_state["determining_factor"],
            custom_delays=state_custom_delays,
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

        if create_actors_df_flag:
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

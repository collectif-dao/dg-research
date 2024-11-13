import collections.abc
from datetime import datetime
from pathlib import Path

from radcad import Backend, Engine, Experiment, Model, Simulation

from experiments.utils import DualGovernanceParameters, construct_state_data, get_batch_hash, get_simulation_hash
from model.state_update_blocks import state_update_blocks
from model.sys_params import sys_params
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.reaction_time import ModeledReactions
from model.types.scenario import Scenario
from model.utils.initialization import generate_initial_state
from specs.utils import percent_base

collections.Hashable = collections.abc.Hashable


def setup_simulation_batch(
    batch_index: int,
    batch_size: int,
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
    time_profiling: bool = False,
    save_files: bool = True,
    skip_existing_batches: bool = False,
):
    """Setup a single batch of simulations"""
    if dual_governance_params is None:
        dual_governance_params = [DualGovernanceParameters()]

    simulations = []
    simulation_hashes = []

    params_per_run = len(dual_governance_params)
    start_run = batch_index * batch_size // params_per_run
    end_run = min(monte_carlo_runs, ((batch_index + 1) * batch_size + params_per_run - 1) // params_per_run)

    simulation_count = 0

    for run in range(start_run, end_run):
        seed_str = seed + run

        for params in dual_governance_params:
            if len(simulations) >= batch_size:
                print(f"Reached batch size limit at {len(simulations)} simulations")
                break

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
            simulation_count += 1

    if not simulations:
        return None, None

    print(f"Created {simulation_count} simulations for batch {batch_index}")

    batch_hash = get_batch_hash(simulation_hashes, timesteps)
    batch_folder_path = Path(out_dir).joinpath(f"batch_{batch_hash}/")

    if batch_folder_path.exists() and not skip_existing_batches:
        required_files = ["common_data.parquet", "proposals_data.parquet", "timestep_data.parquet"]
        if all(batch_folder_path.joinpath(f).is_file() for f in required_files):
            print(f"Skipping batch {batch_hash} as it already exists with required files.")
            return None, None

    if save_files:
        batch_folder_path.mkdir(exist_ok=True, parents=True)

    for simulation in simulations:
        simulation.model.initial_state["outpath"] = batch_folder_path
        simulation.model.state["outpath"] = batch_folder_path

    experiment = Experiment(simulations)
    experiment.engine = Engine(
        backend=Backend.MULTIPROCESSING, raise_exceptions=False, drop_substeps=not time_profiling, deepcopy=False
    )

    return experiment, simulation_hashes


def run_simulation_batches(
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
    time_profiling: bool = False,
    save_files: bool = True,
    batch_size: int = 100,
    skip_existing_batches: bool = False,
    execute_simulations: bool = True,
):
    """Run simulations in batches"""
    dual_governance_params = dual_governance_params or [DualGovernanceParameters()]

    total_simulations = monte_carlo_runs * len(dual_governance_params)
    batch_count = (total_simulations + batch_size - 1) // batch_size
    print(f"Total simulations: {total_simulations}")
    print(f"Dual governance params: {len(dual_governance_params)}")
    print(f"Monte Carlo runs: {monte_carlo_runs}")

    all_simulation_hashes = []

    print(f"Starting simulation with {total_simulations} total simulations in {batch_count} batches")

    for batch_idx in range(batch_count):
        print(f"Processing batch {batch_idx + 1}/{batch_count}")

        experiment, simulation_hashes = setup_simulation_batch(
            batch_index=batch_idx,
            batch_size=batch_size,
            timesteps=timesteps,
            monte_carlo_runs=monte_carlo_runs,
            scenario=scenario,
            proposal_types=proposal_types,
            proposal_subtypes=proposal_subtypes,
            proposals_generation=proposals_generation,
            proposals=proposals,
            attackers=attackers,
            defenders=defenders,
            seed=seed,
            simulation_starting_time=simulation_starting_time,
            out_dir=out_dir,
            dual_governance_params=dual_governance_params,
            max_actors=max_actors,
            institutional_threshold=institutional_threshold,
            labeled_addresses=labeled_addresses,
            time_profiling=time_profiling,
            save_files=save_files,
            skip_existing_batches=skip_existing_batches,
        )

        if experiment is None:
            continue

        try:
            if execute_simulations:
                experiment.run()
            all_simulation_hashes.extend(simulation_hashes)
        except Exception as e:
            print(f"Error in batch {batch_idx + 1}: {e}")
            raise
        finally:
            del experiment
            import gc

            gc.collect()

    print(f"Completed {len(all_simulation_hashes)} simulations")
    return all_simulation_hashes

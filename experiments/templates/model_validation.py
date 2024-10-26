from experiments.simulation_configuration import SIMULATION_TIME, calculate_timesteps, get_path
from experiments.utils import save_execution_result, setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 1
# SEED = 5322 # veto loop somehow
# SEED = 1000 # veto loop somehow
# SEED = 2000 # veto loop somehow
SEED = 392 # veto loop somehow
TIMESTEPS = calculate_timesteps(3)
# TIMESTEPS = 2400


def create_experiment(simulation_name: str = "model_validation"):
    out_path = get_path()

    experiment, simulation_hashes = setup_simulation(
        timesteps=TIMESTEPS,
        monte_carlo_runs=MONTE_CARLO_RUNS,
        scenario=Scenario.HappyPath,
        proposal_types=ProposalType.Random,
        proposal_subtypes=ProposalSubType.NoEffect,
        proposals_generation=ProposalGeneration.Random,
        seed=SEED,
        simulation_starting_time=SIMULATION_TIME,
        out_dir=out_path.joinpath(simulation_name),
    )
    # experiment.after_experiment = lambda experiment=None: save_execution_result(
    #     experiment, simulation_name, TIMESTEPS, out_path
    # )

    return experiment, simulation_hashes

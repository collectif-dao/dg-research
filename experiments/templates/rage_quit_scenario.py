from experiments.simulation_configuration import SIMULATION_TIME, calculate_timesteps, get_path
from experiments.utils import save_execution_result, setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 1
SEED = 141
SCENARIO = Scenario.SingleAttack
TIMESTEPS = calculate_timesteps(3)

proposals = [
    Proposal(
        timestep=2,
        damage=40,
        proposal_type=ProposalType.Negative,
        sub_type=ProposalSubType.NoEffect,
        proposer="0xc329400492c6ff2438472d4651ad17389fcb843a",
        cancelable=False,
    ),
]

attackers = {"0xc329400492c6ff2438472d4651ad17389fcb843a"}
defenders = {}


def create_experiment(simulation_name: str = "rage_quit"):
    out_path = get_path()

    experiment, simulation_hashes = setup_simulation(
        timesteps=TIMESTEPS,
        monte_carlo_runs=MONTE_CARLO_RUNS,
        scenario=SCENARIO,
        proposal_types=ProposalType.Negative,
        proposal_subtypes=ProposalSubType.NoEffect,
        proposals_generation=ProposalGeneration.Random,
        proposals=proposals,
        attackers=attackers,
        defenders=defenders,
        seed=SEED,
        simulation_starting_time=SIMULATION_TIME,
        out_dir=out_path.joinpath(simulation_name),
    )

    experiment.after_experiment = lambda experiment=None: save_execution_result(
        experiment, simulation_name, TIMESTEPS, out_path
    )

    return experiment, simulation_hashes

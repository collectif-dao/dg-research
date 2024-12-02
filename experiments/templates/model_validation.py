from experiments.simulation_configuration import SIMULATION_TIME, calculate_timesteps, get_path
from experiments.utils import setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 100
# MONTE_CARLO_RUNS = 100
SEED = 6050
# SEED = 10000
TIMESTEPS = calculate_timesteps(3)
# TIMESTEPS = 2

proposals = [
    Proposal(
        timestep=1,
        damage=-15,
        proposal_type=ProposalType.Positive,
        sub_type=ProposalSubType.NoEffect,
        proposer="0xae09915bc866661c2a6f93c51356216c2895f9aa",
        cancelable=True,
    ),
]

# first_thresholds = [1, 1.25]
# second_thresholds = [10]
# dual_governance_params = [
#     DualGovernanceParameters(first_rage_quit_support=thresh1, second_rage_quit_support=thresh2)
#     for thresh1 in first_thresholds
#     for thresh2 in second_thresholds
# ]

# attackers = {"0xc329400492c6ff2438472d4651ad17389fcb843a"}
# defenders = {}


def create_experiment(simulation_name: str = "model_validation", return_template: bool = False):
    out_path = get_path()

    template_params = {
        "timesteps": TIMESTEPS,
        "monte_carlo_runs": MONTE_CARLO_RUNS,
        "scenario": Scenario.HappyPath,
        "proposal_types": ProposalType.Random,
        "proposal_subtypes": ProposalSubType.NoEffect,
        "proposals_generation": ProposalGeneration.Random,
        "seed": SEED,
        "simulation_starting_time": SIMULATION_TIME,
        # "dual_governance_params": dual_governance_params,
    }

    if return_template:
        return None, template_params

    experiment, simulation_hashes = setup_simulation(**template_params, out_dir=out_path.joinpath(simulation_name))

    experiment.after_experiment = None

    return experiment, simulation_hashes

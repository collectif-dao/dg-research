from experiments.simulation_configuration import SIMULATION_TIME, calculate_timesteps, get_path
from experiments.utils import DualGovernanceParameters, setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 1
SEED = 188
SCENARIO = Scenario.ConstantVetoSignallingLoop
TIMESTEPS = calculate_timesteps(3)

proposals = [
    Proposal(
        timestep=2,
        damage=-15,
        proposal_type=ProposalType.Positive,
        sub_type=ProposalSubType.NoEffect,
        proposer="0x6625c6332c9f91f2d27c304e729b86db87a3f504",
    ),
]

attackers = {
    "0x5eea56d346aa5bc5aea1786169e1f4b8699e882d",
    "0x6625c6332c9f91f2d27c304e729b86db87a3f504",
    "0x5313b39bf226ced2332c81eb97bb28c6fd50d1a3",
}
defenders = {}

dual_governance_params = [
    DualGovernanceParameters(first_rage_quit_support=1, second_rage_quit_support=10),
]


def create_experiment(simulation_name: str = "constant_veto_signalling_loop", return_template: bool = False):
    out_path = get_path()

    template_params = {
        "timesteps": TIMESTEPS,
        "monte_carlo_runs": MONTE_CARLO_RUNS,
        "scenario": SCENARIO,
        "proposal_types": ProposalType.Positive,
        "proposal_subtypes": ProposalSubType.NoEffect,
        "proposals_generation": ProposalGeneration.Random,
        "proposals": proposals,
        "attackers": attackers,
        "defenders": defenders,
        "seed": SEED,
        "simulation_starting_time": SIMULATION_TIME,
        "dual_governance_params": dual_governance_params,
    }

    if return_template:
        return None, template_params

    experiment, simulation_hashes = setup_simulation(**template_params, out_dir=out_path.joinpath(simulation_name))
    experiment.after_experiment = None

    return experiment, simulation_hashes

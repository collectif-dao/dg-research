from experiments.simulation_configuration import SIMULATION_TIME, calculate_timesteps, get_path
from experiments.utils import DualGovernanceParameters, setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 1
SEED = 141
SCENARIO = Scenario.SingleAttack
TIMESTEPS = calculate_timesteps(1)

proposals = [
    Proposal(
        timestep=2,
        damage=100,
        proposal_type=ProposalType.Danger,
        sub_type=ProposalSubType.FundsStealing,
        proposer="0xc329400492c6ff2438472d4651ad17389fcb843a",
        attack_targets={
            "0xb671e841a8e6db528358ed385983892552ef422f",
            "0x4b4eec1ddc9420a5cc35a25f5899dc5993f9e586",
            "0x47176b2af9885dc6c4575d4efd63895f7aaa4790",
        },
    ),
]

attackers = {"0xc329400492c6ff2438472d4651ad17389fcb843a"}
defenders = {}

dual_governance_params = [
    DualGovernanceParameters(first_rage_quit_support=1, second_rage_quit_support=10),
    DualGovernanceParameters(first_rage_quit_support=2, second_rage_quit_support=12),
]


def create_experiment(simulation_name: str = "withdrawal_queue_replacement", return_template: bool = False):
    out_path = get_path()

    template_params = {
        "timesteps": TIMESTEPS,
        "monte_carlo_runs": MONTE_CARLO_RUNS,
        "scenario": SCENARIO,
        "proposal_types": ProposalType.Danger,
        "proposal_subtypes": ProposalSubType.FundsStealing,
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

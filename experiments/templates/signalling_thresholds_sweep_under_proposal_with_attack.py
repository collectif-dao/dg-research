from experiments.simulation_configuration import SIMULATION_TIME, calculate_timesteps, get_path
from experiments.utils import DualGovernanceParameters, save_execution_result, setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 10
SEED = 188
SCENARIO = Scenario.SingleAttack
TIMESTEPS = calculate_timesteps(0.5)

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

# first_thresholds = [0.5, 1, 3, 5]
# second_thresholds = [10, 15]
first_thresholds = [0.5, 1, 3]
second_thresholds = [5, 10, 15]
dual_governance_params = [
    DualGovernanceParameters(first_rage_quit_support=thresh1, second_rage_quit_support=thresh2)
    for thresh1 in first_thresholds
    for thresh2 in second_thresholds]
# dual_governance_params = [
#     DualGovernanceParameters(first_rage_quit_support=1, second_rage_quit_support=10),
#     DualGovernanceParameters(first_rage_quit_support=2, second_rage_quit_support=12),
# ]

def create_experiment(simulation_name: str = "signalling_thresholds_sweep_under_proposal_with_attack"):
    out_path = get_path()

    experiment, simulation_hashes = setup_simulation(
        timesteps=TIMESTEPS,
        monte_carlo_runs=MONTE_CARLO_RUNS,
        scenario=SCENARIO,
        proposal_types=ProposalType.Danger,
        proposal_subtypes=ProposalSubType.FundsStealing,
        proposals_generation=ProposalGeneration.NoGeneration,
        proposals=proposals,
        attackers=attackers,
        defenders=defenders,
        seed=SEED,
        simulation_starting_time=SIMULATION_TIME,
        out_dir=out_path.joinpath(simulation_name),
        dual_governance_params=dual_governance_params,
    )

    experiment.after_experiment = lambda experiment=None: save_execution_result(
        experiment, simulation_name, TIMESTEPS, out_path, create_actors_df=False
    )

    return experiment, simulation_hashes

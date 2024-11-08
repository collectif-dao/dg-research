from experiments.simulation_configuration import SIMULATION_TIME, calculate_timesteps, get_path
from experiments.utils import DualGovernanceParameters, setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 1
# SEED = 5321
SEED = 5323
TIMESTEPS = calculate_timesteps(3)
# TIMESTEPS = 2

# MONTE_CARLO_RUNS = 25
# SEED = MONTE_CARLO_RUNS * 1
SCENARIO = Scenario.SingleAttack


def proper_save(experiment):
    import pickle

    import pandas as pd

    with open("results/simulations/model_validation/result.pkl", "wb") as f:
        df = pd.DataFrame(experiment.results)
        pickle.dump(df, f)


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
# attackers = {
#     "0x48d62ed012e327faacb9c8d2a56330e215da0575",
#     "0xa17581a9e3356d9a858b789d68b4d866e593ae94",
#     "0x3c22ec75ea5d745c78fc84762f7f1e6d82a2c5bf",
#     "0x5eea56d346aa5bc5aea1786169e1f4b8699e882d",
#     "0x6625c6332c9f91f2d27c304e729b86db87a3f504",
#     "0x5313b39bf226ced2332c81eb97bb28c6fd50d1a3",
# }
# defenders = {}
# first_thresholds = [1, 1.25]
# second_thresholds = [10]
# dual_governance_params = [
#     DualGovernanceParameters(first_rage_quit_support=thresh1, second_rage_quit_support=thresh2)
#     for thresh1 in first_thresholds
#     for thresh2 in second_thresholds
# ]


# proposals = [
#     Proposal(
#         timestep=5,
#         damage=100,
#         proposal_type=ProposalType.Danger,
#         sub_type=ProposalSubType.FundsStealing,
#         proposer="0xc329400492c6ff2438472d4651ad17389fcb843a",
#         attack_targets={
#             "0xb671e841a8e6db528358ed385983892552ef422f",
#             "0x4b4eec1ddc9420a5cc35a25f5899dc5993f9e586",
#             "0x47176b2af9885dc6c4575d4efd63895f7aaa4790",
#         },
#     ),
# ]

# attackers = {"0xc329400492c6ff2438472d4651ad17389fcb843a"}
# defenders = {}

first_thresholds = [1]
second_thresholds = [10]
dual_governance_params = [
    DualGovernanceParameters(first_rage_quit_support=thresh1, second_rage_quit_support=thresh2)
    for thresh1 in first_thresholds
    for thresh2 in second_thresholds
]


def create_experiment(simulation_name: str = "model_validation_asd", time_profiling=False, create_actors_df_flag=False):
    out_path = get_path()

    experiment, simulation_hashes = setup_simulation(
        timesteps=TIMESTEPS,
        monte_carlo_runs=MONTE_CARLO_RUNS,
        scenario=Scenario.HappyPath,
        proposal_types=ProposalType.Positive,
        proposal_subtypes=ProposalSubType.NoEffect,
        proposals_generation=ProposalGeneration.Random,
        proposals=proposals,
        seed=SEED,
        simulation_starting_time=SIMULATION_TIME,
        out_dir=out_path.joinpath(simulation_name),
        time_profiling=time_profiling,
        # attackers=attackers,
        # dual_governance_params=dual_governance_params,
        # timesteps=TIMESTEPS,
        # monte_carlo_runs=MONTE_CARLO_RUNS,
        # scenario=SCENARIO,
        # proposal_types=ProposalType.Danger,
        # proposal_subtypes=ProposalSubType.FundsStealing,
        # proposals_generation=ProposalGeneration.NoGeneration,
        # proposals=proposals,
        # attackers=attackers,
        # defenders=defenders,
        # seed=SEED,
        # simulation_starting_time=SIMULATION_TIME,
        # out_dir=out_path.joinpath(simulation_name),
        # dual_governance_params=dual_governance_params,
    )

    # experiment.after_experiment = lambda experiment=None: save_execution_result(
    #     experiment, simulation_name, TIMESTEPS, out_path, drop_substeps=(not time_profiling)
    # )
    # experiment.after_experiment = proper_save
    experiment.after_experiment = None

    return experiment, simulation_hashes

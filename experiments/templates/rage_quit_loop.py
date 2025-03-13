import numpy as np

from experiments.simulation_configuration import SIMULATION_TIME, calculate_timesteps, get_path
from experiments.utils import DualGovernanceParameters, setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 1
SEED = 1888
SCENARIO = Scenario.RageQuitLoop
TIMESTEPS = calculate_timesteps(simulation_months=48)
# TIMESTEPS = 1800

proposals = [
    Proposal(
        timestep=2,
        damage=-15,
        proposal_type=ProposalType.Positive,
        sub_type=ProposalSubType.NoEffect,
        proposer="0x5eea56d346aa5bc5aea1786169e1f4b8699e882d",
    ),
]

attackers = {
    "0x5eea56d346aa5bc5aea1786169e1f4b8699e882d",
    # "0x5313b39bf226ced2332c81eb97bb28c6fd50d1a3",
}
defenders = {}

total_balance = 9000000


def get_share(k):
    return k / (1 - k)


# shares = np.array([0.1, 0.19, 0.271, 0.344]) + 0.0001
# shares = np.array([0.06, 0.1075, 0.1526, 0.1955])
shares = np.array([0.06, 0.1075, 0.1526, 0.1955])
# shares = np.array([0.1075]) + 0.0001
# shares = np.array([0.1, 0.2, 0.3, 0.4]) + 0.03
attacker_funds_list = [int(np.round(total_balance * get_share(share))) for share in shares]
print(attacker_funds_list)
lido_exit_share_list = [0.3]
deposit_caps = [300_000]
dual_governance_params = [
    DualGovernanceParameters(
        first_rage_quit_support=1,
        second_rage_quit_support=5,
        attacker_funds=funds,
        lido_exit_share=share,
        deposit_cap=cap,
        process_deposits=True,
    )
    for funds in attacker_funds_list
    for share in lido_exit_share_list
    for cap in deposit_caps
]


def create_experiment(simulation_name: str = "rage_quit_loop", return_template: bool = False):
    out_path = get_path()

    template_params = {
        "timesteps": TIMESTEPS,
        "monte_carlo_runs": MONTE_CARLO_RUNS,
        "scenario": SCENARIO,
        "proposal_types": ProposalType.Positive,
        "proposal_subtypes": ProposalSubType.NoEffect,
        "proposals_generation": ProposalGeneration.NoGeneration,
        "proposals": proposals,
        "attackers": attackers,
        "defenders": defenders,
        "seed": SEED,
        "simulation_starting_time": SIMULATION_TIME,
        "dual_governance_params": dual_governance_params,
        "normalize_funds": total_balance // 2,
    }

    if return_template:
        return None, template_params

    experiment, simulation_hashes = setup_simulation(**template_params, out_dir=out_path.joinpath(simulation_name))
    experiment.after_experiment = None

    return experiment, simulation_hashes

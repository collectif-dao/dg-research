import numpy as np

from experiments.simulation_configuration import (SIMULATION_TIME,
                                                  calculate_timesteps,
                                                  get_path)
from experiments.utils import DualGovernanceParameters, setup_simulation
from model.types.proposal_type import (ProposalGeneration, ProposalSubType,
                                       ProposalType)
from model.types.proposals import Proposal, ProposalsEffect
from model.types.scenario import Scenario

# from model.utils.address_labeling import assign_labels_by_funds_threshold


def get_attacker_funds_from_share(total_balance, share):
    return total_balance * share / (1 - share)

MONTE_CARLO_RUNS = 1000
SEED = 141
SCENARIO = Scenario.SingleAttack
# TIMESTEPS = calculate_timesteps(1)
TIMESTEPS = 75

proposal_effect: ProposalsEffect = ProposalsEffect()
proposal_effect.add_effect("Decentralized", 0)
proposal_effect.add_effect("Institutional", 35)
# labeled_addresses = assign_labels_by_funds_threshold(3000, "Institutional", "Decentralized")

attackers = {"0x91bef2fd282aaa7612c593c4d83c0efaf6200954"}
defenders = {}

proposals = [
    Proposal(
        timestep=2,
        damage=100,
        proposal_type=ProposalType.Danger,
        sub_type=ProposalSubType.FundsStealing,
        proposer=list(attackers)[0],
        # effects=proposal_effect,
    ),
    # Proposal(
    #     timestep=252,
    #     damage=-25,
    #     proposal_type=ProposalType.Negative,
    #     sub_type=ProposalSubType.NoEffect,
    #     proposer="0xc329400492c6ff2438472d4651ad17389fcb843a",
    #     attack_targets={
    #         "0x176f3dab24a159341c0509bb36b833e7fdd0a132",
    #         "0x3c22ec75ea5d745c78fc84762f7f1e6d82a2c5bf",
    #     },
    #     # cancelable=False,
    # ),
]

# first_rage_quit_support_list = [1.75]
# dual_governance_params = [
#     DualGovernanceParameters(first_rage_quit_support=thresh, second_rage_quit_support=10)
#     for thresh in first_rage_quit_support_list
# ]
total_balance = 8996374.56750506 # Calculated for attacker 0x91bef2fd282aaa7612c593c4d83c0efaf6200954
min_share = 0.25
max_share = 0.55
step = 0.05
shares = np.arange(min_share, max_share, step)
attacker_funds_list = [get_attacker_funds_from_share(total_balance, share) for share in shares]
first_thresholds = [1]
second_thresholds = [10]
dual_governance_params = [
    DualGovernanceParameters(first_rage_quit_support=thresh1, second_rage_quit_support=thresh2, attacker_funds=funds)
    for thresh1 in first_thresholds
    for thresh2 in second_thresholds
    for funds in attacker_funds_list
]


def create_experiment(simulation_name: str = "withdrawal_queue_replacement", return_template: bool = False):
    out_path = get_path()

    template_params = {
        "timesteps": TIMESTEPS,
        "monte_carlo_runs": MONTE_CARLO_RUNS,
        "scenario": SCENARIO,
        "proposal_types": ProposalType.Danger,
        "proposal_subtypes": ProposalSubType.FundsStealing,
        "proposals_generation": ProposalGeneration.NoGeneration,
        "proposals": proposals,
        "attackers": attackers,
        "defenders": defenders,
        "seed": SEED,
        "simulation_starting_time": SIMULATION_TIME,
        "dual_governance_params": dual_governance_params,
        "institutional_threshold": 3000,
    }

    if return_template:
        return None, template_params

    experiment, simulation_hashes = setup_simulation(**template_params, out_dir=out_path.joinpath(simulation_name))
    experiment.after_experiment = None

    return experiment, simulation_hashes

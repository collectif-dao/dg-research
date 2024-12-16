import numpy as np

from experiments.simulation_configuration import SIMULATION_TIME, get_path
from experiments.utils import DualGovernanceParameters, setup_simulation
from model.types.proposal_type import (ProposalGeneration, ProposalSubType,
                                       ProposalType)
from model.types.proposals import Proposal, ProposalsEffect
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 1
SEED = 141
SCENARIO = Scenario.SingleAttack
TIMESTEPS = 450

attackers = {"0x91bef2fd282aaa7612c593c4d83c0efaf6200954"}
defenders = {}

proposals = [
    Proposal(
        timestep=2,
        damage=100,
        proposal_type=ProposalType.Danger,
        sub_type=ProposalSubType.FundsStealing,
        proposer=list(attackers)[0],
        cancelable=False
    )
]

first_thresholds = [1]
second_thresholds = [10]
after_schedule_delay_list = [100]
dual_governance_params = [
    DualGovernanceParameters(
        first_rage_quit_support=thresh1,
        second_rage_quit_support=thresh2,
        after_schedule_delay=delay,
    )
    for thresh1 in first_thresholds
    for thresh2 in second_thresholds
    for delay in after_schedule_delay_list
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

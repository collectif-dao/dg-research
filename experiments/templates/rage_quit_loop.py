from experiments.simulation_configuration import SIMULATION_TIME, calculate_timesteps, get_path
from experiments.utils import DualGovernanceParameters, setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 100
SEED = 1888
SCENARIO = Scenario.RageQuitLoop
TIMESTEPS = calculate_timesteps(simulation_months=24)
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

attacker_funds_list = [2_000_000]
lido_exit_share_list = [0.3]
deposit_caps = [300_000]
dual_governance_params = [
    DualGovernanceParameters(
        first_rage_quit_support=1,
        second_rage_quit_support=10,
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
    }

    if return_template:
        return None, template_params

    experiment, simulation_hashes = setup_simulation(**template_params, out_dir=out_path.joinpath(simulation_name))
    experiment.after_experiment = None

    return experiment, simulation_hashes

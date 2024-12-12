from experiments.simulation_configuration import SIMULATION_TIME, get_path
from experiments.utils import DualGovernanceParameters, setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 1000
SEED = 4121
SCENARIO = Scenario.CoordinatedAttack
TIMESTEPS = 2

attackers = {"0x91bef2fd282aaa7612c593c4d83c0efaf6200954"}

attacker_funds_list = [1000]
determining_factors = [10, 20, 30, 40, 50]
dual_governance_params = [
    DualGovernanceParameters(
        first_rage_quit_support=1,
        second_rage_quit_support=10,
        attacker_funds=funds,
        determining_factor=determining_factor,
    )
    for funds in attacker_funds_list
    for determining_factor in determining_factors
]

proposals = [
    Proposal(
        timestep=2,
        damage=100,
        proposal_type=ProposalType.Danger,
        sub_type=ProposalSubType.Bribing,
        proposer=list(attackers)[0],
        attack_targets_determination=True,
        # attack_targets={
        #     "0x5eea56d346aa5bc5aea1786169e1f4b8699e882d",
        #     "0x11dd5d87e5bce946b3bad36685901095e063f48e",
        #     "0x5313b39bf226ced2332c81eb97bb28c6fd50d1a3",
        #     "0x02ed4a07431bcc26c5519ebf8473ee221f26da8b",
        # },
    ),
]


def create_experiment(simulation_name: str = "bribed_withdrawal_queue_replacement", return_template: bool = False):
    out_path = get_path()

    template_params = {
        "timesteps": TIMESTEPS,
        "monte_carlo_runs": MONTE_CARLO_RUNS,
        "scenario": SCENARIO,
        "proposal_types": ProposalType.Danger,
        "proposal_subtypes": ProposalSubType.Bribing,
        "proposals_generation": ProposalGeneration.NoGeneration,
        "proposals": proposals,
        "attackers": attackers,
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

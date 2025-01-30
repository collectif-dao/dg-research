from experiments.simulation_configuration import SIMULATION_TIME, get_path
from experiments.utils import DualGovernanceParameters, setup_simulation
from model.sys_params import CustomDelays
from model.types.proposal_type import (ProposalGeneration, ProposalSubType,
                                       ProposalType)
from model.types.proposals import Proposal
from model.types.reaction_time import ModeledReactions
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 100
SEED = 241
SCENARIO = Scenario.SingleAttack
TIMESTEPS = 1500

attackers = {"0x91bef2fd282aaa7612c593c4d83c0efaf6200954"}
defenders = {}

proposals = [
    Proposal(
        timestep=2,
        damage=100,
        proposal_type=ProposalType.Danger,
        sub_type=ProposalSubType.FundsStealing,
        proposer=list(attackers)[0],
        cancelable=False,
    )
]

first_thresholds = [1]
second_thresholds = [12, 15]

custom_delays = [
    CustomDelays(slow_max_delay=3600 * 24 * 15, slow_precompute_params=(0.1742925521297363, 0, 864000.0)),
    CustomDelays(slow_max_delay=3600 * 24 * 30, slow_precompute_params=(0.2316921328693872, 0, 1512000.0)),
    CustomDelays(slow_max_delay=3600 * 24 * 35, slow_precompute_params=(0.2316921328693872, 0, 1512000.0)),
    CustomDelays(slow_max_delay=3600 * 24 * 40, slow_precompute_params=(0.25266499110519525, 0, 2160000.0)),
    CustomDelays(slow_max_delay=3600 * 24 * 45, slow_precompute_params=(0.25266499110519525, 0, 2160000.0)),
]
dual_governance_params = [
    DualGovernanceParameters(
        first_rage_quit_support=thresh1,
        second_rage_quit_support=thresh2,
        custom_delays=custom_delay,
        modeled_reactions=ModeledReactions.Normal,
        # modeled_reactions=modeled_reactions,
        # after_schedule_delay=1000000
    )
    for custom_delay in custom_delays
    for thresh1 in first_thresholds
    for thresh2 in second_thresholds
    # for modeled_reactions in [ModeledReactions.Normal, ModeledReactions.Slowed, ModeledReactions.Accelerated]
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
        "wallet_csv_name": "stETH token distribution  - stETH+wstETH holders.csv",
    }

    if return_template:
        return None, template_params

    experiment, simulation_hashes = setup_simulation(**template_params, out_dir=out_path.joinpath(simulation_name))
    experiment.after_experiment = None

    return experiment, simulation_hashes

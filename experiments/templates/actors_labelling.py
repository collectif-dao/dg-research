from experiments.simulation_configuration import SIMULATION_TIME, get_path
from experiments.utils import DualGovernanceParameters, setup_simulation
from model.types.proposal_type import (ProposalGeneration, ProposalSubType,
                                       ProposalType)
from model.types.proposals import Proposal, ProposalsEffect
from model.types.scenario import Scenario
from model.utils.address_labeling import assign_labels_by_percentage

MONTE_CARLO_RUNS = 1000
SEED = 1
SCENARIO = Scenario.HappyPath
TIMESTEPS = 75

proposal_effect: ProposalsEffect = ProposalsEffect()
proposal_effect.add_effect("Decentralized", 0)
proposal_effect.add_effect("Centralized", 100)

labeled_addresses = assign_labels_by_percentage(
    main_label="Decentralized",
    counter_label="Centralized",
)

labeled_percentages = [43]

proposals = [
    Proposal(
        timestep=2,
        damage=0,
        proposal_type=ProposalType.Random,
        sub_type=ProposalSubType.NoEffect,
        proposer="0x6625c6332c9f91f2d27c304e729b86db87a3f504",
        effects=proposal_effect,
        cancelable=True,
    ),
]

attackers = {}
defenders = {}


dual_governance_params = [
    DualGovernanceParameters(first_rage_quit_support=1, second_rage_quit_support=10, determining_factor=percentage)
    for percentage in labeled_percentages
]


def create_experiment(simulation_name: str = "actors_labelling", return_template: bool = False):
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
        "labeled_addresses": labeled_addresses,
        "institutional_threshold": 3000,
    }

    if return_template:
        return None, template_params

    experiment, simulation_hashes = setup_simulation(**template_params, out_dir=out_path.joinpath(simulation_name))

    experiment.after_experiment = None

    return experiment, simulation_hashes

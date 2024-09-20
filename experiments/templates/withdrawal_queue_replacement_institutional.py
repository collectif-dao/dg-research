from experiments.simulation_configuration import SIMULATION_TIME, calculate_timesteps, get_path
from experiments.utils import save_execution_result, setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.reaction_time import ModeledReactions
from model.types.scenario import Scenario

MONTE_CARLO_RUNS = 5
SEED = 141
SCENARIO = Scenario.SingleAttack
TIMESTEPS = calculate_timesteps(3)

proposals = [
    Proposal(
        timestep=2,
        damage=45,
        proposal_type=ProposalType.Danger,
        sub_type=ProposalSubType.FundsStealing,
        proposer="0x98078db053902644191f93988341e31289e1c8fe",
        attack_targets={
            "0xb671e841a8e6db528358ed385983892552ef422f",
            "0x4b4eec1ddc9420a5cc35a25f5899dc5993f9e586",
            "0x47176b2af9885dc6c4575d4efd63895f7aaa4790",
        },
    ),
]

attackers = {"0x98078db053902644191f93988341e31289e1c8fe", "0xc329400492c6ff2438472d4651ad17389fcb843a"}
defenders = {"0x3e40d73eb977dc6a537af587d48316fee66e9c8c"}


def create_experiment(simulation_name: str = "withdrawal_queue_replacement_institutional"):
    out_path = get_path()

    experiment, simulation_hashes = setup_simulation(
        timesteps=TIMESTEPS,
        monte_carlo_runs=MONTE_CARLO_RUNS,
        scenario=SCENARIO,
        proposal_types=ProposalType.Danger,
        proposal_subtypes=ProposalSubType.FundsStealing,
        proposals_generation=ProposalGeneration.Random,
        proposals=proposals,
        attackers=attackers,
        defenders=defenders,
        seed=SEED,
        simulation_starting_time=SIMULATION_TIME,
        out_dir=out_path.joinpath(simulation_name),
        institutional_threshold=0.05
    )

    experiment.after_experiment = lambda experiment=None: save_execution_result(
        experiment, simulation_name, TIMESTEPS, out_path
    )

    return experiment, simulation_hashes

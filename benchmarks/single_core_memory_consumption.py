from datetime import datetime
from pathlib import Path

from radcad import Backend, Engine

from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.proposals import Proposal
from model.types.scenario import Scenario
from model.utils.simulation import save_execution_result, setup_simulation

out_path = Path("results/simulations")
out_path.mkdir(exist_ok=True)

MONTE_CARLO_RUNS = 2
TIMESTEPS = 100
SEED = 141
SIMULATION_TIME = datetime(2024, 9, 1)
SCENARIO = Scenario.SingleAttack

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
    out_dir=out_path,
)
experiment.engine = Engine(backend=Backend.SINGLE_PROCESS, processes=1, raise_exceptions=False, drop_substeps=True)
experiment.after_experiment = lambda experiment=None: save_execution_result(experiment, TIMESTEPS, out_path)
simulations = experiment.get_simulations()

# # if len(simulations) != 0:
result = experiment.run()

# result = merge_simulation_results(simulation_hashes, out_path)
# post_processing = postprocessing(result)

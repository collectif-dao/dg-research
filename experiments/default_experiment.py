from radcad import Backend, Engine

from experiments.simulation_configuration import MONTE_CARLO_RUNS, SIMULATION_TIME, TIMESTEPS, get_path
from experiments.utils import setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalSubType, ProposalType
from model.types.scenario import Scenario

SEED = 13

out_path = get_path()

default_experiment, simulation_hashes = setup_simulation(
    timesteps=TIMESTEPS,
    monte_carlo_runs=MONTE_CARLO_RUNS,
    scenario=Scenario.HappyPath,
    proposal_types=ProposalType.Random,
    proposal_subtypes=ProposalSubType.NoEffect,
    proposals_generation=ProposalGeneration.Random,
    seed=SEED,
    simulation_starting_time=SIMULATION_TIME,
    out_dir=out_path,
)
default_experiment.engine = Engine(backend=Backend.SINGLE_PROCESS, processes=1, raise_exceptions=False)
default_experiment.after_experiment = lambda experiment=None: None
default_experiment.engine.deepcopy = False
default_experiment.engine.drop_substeps = True

from datetime import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from experiments.default_experiment import SEED
from experiments.simulation_configuration import TIMESTEPS, get_path
from experiments.utils import DualGovernanceParameters, setup_simulation
from model.types.proposal_type import ProposalGeneration, ProposalType
from model.types.proposals import ProposalSubType
from model.types.scenario import Scenario
from specs.utils import percent_base


@given(
    dual_governance_params=st.lists(
        st.builds(
            DualGovernanceParameters,
            first_rage_quit_support=st.one_of(st.none(), st.integers(min_value=1, max_value=3)),
            second_rage_quit_support=st.one_of(st.none(), st.integers(min_value=10, max_value=15)),
        ),
        min_size=1,
        max_size=2,
    ),
)
@settings(deadline=None)
def test_setup_simulation(
    dual_governance_params,
):
    scenario = Scenario.HappyPath
    proposal_types = ProposalType.Random
    proposal_subtypes = ProposalSubType.NoEffect
    proposals_generation = ProposalGeneration.Random
    timesteps = TIMESTEPS
    seed = SEED
    monte_carlo_runs = 3
    out_path = get_path()
    simulation_starting_time = datetime(2024, 9, 1)
    initial_proposals = []
    attackers = set()
    defenders = set()

    experiment, simulation_hashes = setup_simulation(
        timesteps=timesteps,
        monte_carlo_runs=monte_carlo_runs,
        scenario=scenario,
        proposal_types=proposal_types,
        proposal_subtypes=proposal_subtypes,
        proposals_generation=proposals_generation,
        proposals=initial_proposals,
        attackers=attackers,
        defenders=defenders,
        seed=seed,
        simulation_starting_time=simulation_starting_time,
        out_dir=out_path,
        dual_governance_params=dual_governance_params,
    )

    assert len(simulation_hashes) == monte_carlo_runs * len(dual_governance_params)
    assert len(simulation_hashes) == len(experiment.simulations)

    simulation_index = 0
    for run in range(monte_carlo_runs):
        for params_index, params in enumerate(dual_governance_params):
            print(f"params that I'm testing are {params}")

            simulation = experiment.simulations[simulation_index]
            assert simulation.timesteps == timesteps
            assert simulation.runs == 1

            if params.first_rage_quit_support is not None:
                assert (
                    simulation.model.initial_state["first_seal_rage_quit_support"]
                    == params.first_rage_quit_support * percent_base
                )

            if params.second_rage_quit_support is not None:
                assert (
                    simulation.model.initial_state["second_seal_rage_quit_support"]
                    == params.second_rage_quit_support * percent_base
                )

            simulation_index += 1

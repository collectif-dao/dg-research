from datetime import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from experiments.batch import setup_simulation_batch
from experiments.default_experiment import SEED
from experiments.simulation_configuration import TIMESTEPS, get_path
from experiments.utils import DualGovernanceParameters
from model.types.proposal_type import ProposalGeneration, ProposalType
from model.types.proposals import ProposalSubType
from model.types.scenario import Scenario
from specs.utils import percent_base


@given(
    batch_index=st.integers(min_value=0, max_value=2),
    batch_size=st.integers(min_value=1, max_value=5),
    monte_carlo_runs=st.integers(min_value=1, max_value=3),
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
def test_setup_simulation_batch(
    batch_index,
    batch_size,
    monte_carlo_runs,
    dual_governance_params,
):
    scenario = Scenario.HappyPath
    proposal_types = ProposalType.Random
    proposal_subtypes = ProposalSubType.NoEffect
    proposals_generation = ProposalGeneration.Random
    timesteps = TIMESTEPS
    seed = SEED
    out_path = get_path()
    simulation_starting_time = datetime(2024, 9, 1)
    initial_proposals = []
    attackers = set()
    defenders = set()

    experiment, simulation_hashes = setup_simulation_batch(
        batch_index=batch_index,
        batch_size=batch_size,
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
        out_dir=out_path.joinpath("batch_setup_test"),
        dual_governance_params=dual_governance_params,
        save_files=False,
    )

    params_per_run = len(dual_governance_params)
    start_run = batch_index * batch_size // params_per_run
    end_run = min(monte_carlo_runs, ((batch_index + 1) * batch_size + params_per_run - 1) // params_per_run)
    expected_simulations = (end_run - start_run) * params_per_run

    if expected_simulations <= 0:
        assert experiment is None
        assert simulation_hashes is None
        return

    assert len(experiment.simulations) == min(expected_simulations, batch_size)
    assert len(simulation_hashes) == len(experiment.simulations)

    for simulation in experiment.simulations:
        assert simulation.timesteps == timesteps
        assert simulation.runs == 1

        assert simulation.model.initial_state["scenario"] == scenario
        assert simulation.model.initial_state["proposal_types"] == proposal_types
        assert simulation.model.initial_state["proposal_subtypes"] == proposal_subtypes
        assert simulation.model.initial_state["proposal_generation"] == proposals_generation

        assert "simulation_hash" in simulation.model.initial_state
        assert simulation.model.initial_state["simulation_hash"] in simulation_hashes

        first_support = simulation.model.initial_state["first_seal_rage_quit_support"]
        second_support = simulation.model.initial_state["second_seal_rage_quit_support"]

        matching_params = False

        for params in dual_governance_params:
            expected_first = (
                params.first_rage_quit_support if params.first_rage_quit_support is not None else 3
            ) * percent_base
            expected_second = (
                params.second_rage_quit_support if params.second_rage_quit_support is not None else 15
            ) * percent_base

            if first_support == expected_first and second_support == expected_second:
                matching_params = True
                break

        assert matching_params, (
            f"No matching parameters found for simulation with "
            f"first_support={first_support}, second_support={second_support}. "
            f"Available params: {[(p.first_rage_quit_support or 3, p.second_rage_quit_support or 15) for p in dual_governance_params]}"
        )

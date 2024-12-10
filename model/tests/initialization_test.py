from datetime import datetime

from hypothesis import given
from hypothesis import strategies as st

from model.types.proposal_type import ProposalGeneration, ProposalType
from model.types.proposals import ProposalSubType
from model.types.reaction_time import ModeledReactions
from model.types.scenario import Scenario
from model.utils.initialization import generate_initial_state
from specs.parameters import system_parameters
from specs.utils import percent_base


@given(
    scenario=st.sampled_from([Scenario.HappyPath, Scenario.SingleAttack, Scenario.CoordinatedAttack]),
    reactions=st.sampled_from(ModeledReactions),
    proposal_types=st.sampled_from(ProposalType),
    proposal_subtypes=st.sampled_from(ProposalSubType),
    proposal_generation=st.sampled_from(ProposalGeneration),
    seed=st.integers(min_value=1, max_value=1000000000),
    first_rage_quit_threshold=st.one_of(st.none(), st.integers(min_value=1, max_value=5)),
    second_rage_quit_threshold=st.one_of(st.none(), st.integers(min_value=5, max_value=30)),
)
def test_generate_initial_state(
    scenario,
    reactions,
    proposal_types,
    proposal_subtypes,
    proposal_generation,
    seed,
    first_rage_quit_threshold,
    second_rage_quit_threshold,
):
    simulation_starting_time = datetime(2024, 9, 1)
    max_actors = 100
    initial_proposals = []
    attackers = set()
    defenders = set()

    if first_rage_quit_threshold is not None:
        first_rage_quit_threshold = first_rage_quit_threshold * percent_base

    if second_rage_quit_threshold is not None:
        second_rage_quit_threshold = second_rage_quit_threshold * percent_base

    result = generate_initial_state(
        scenario=scenario,
        reactions=reactions,
        proposal_types=proposal_types,
        proposal_subtypes=proposal_subtypes,
        proposal_generation=proposal_generation,
        initial_proposals=initial_proposals,
        max_actors=max_actors,
        attackers=attackers,
        defenders=defenders,
        seed=seed,
        simulation_starting_time=simulation_starting_time,
        first_rage_quit_support=first_rage_quit_threshold,
        second_rage_quit_support=second_rage_quit_threshold,
        save_data_enabled=False,
    )

    assert isinstance(result, dict)
    assert "actors" in result
    assert "lido" in result
    assert "dual_governance" in result
    assert "time_manager" in result

    assert result["proposals"] == initial_proposals
    assert result["non_initialized_proposals"] == []
    assert result["scenario"] == scenario
    assert len(result["attackers"]) >= len(attackers)
    assert result["defenders"].size == 0
    assert result["proposal_types"] == proposal_types
    assert result["proposal_subtypes"] == proposal_subtypes
    assert result["is_active_attack"] is not True
    assert result["proposal_generation"] == proposal_generation
    assert result["seed"] == seed
    assert result["simulation_starting_time"] == int(simulation_starting_time.timestamp())
    assert (
        result["first_seal_rage_quit_support"] == first_rage_quit_threshold
        if first_rage_quit_threshold is not None
        else system_parameters["first_seal_rage_quit_support"] * percent_base
    )
    assert (
        result["second_seal_rage_quit_support"] == second_rage_quit_threshold
        if second_rage_quit_threshold is not None
        else system_parameters["second_seal_rage_quit_support"] * percent_base
    )

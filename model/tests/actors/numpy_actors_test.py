import sys

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from model.actors.actors import Actors
from model.actors.errors import NotEnoughActorStETHBalance, NotEnoughActorWstETHBalance
from model.types.actors import ActorType
from model.types.governance_participation import GovernanceParticipation
from model.types.proposal_type import ProposalSubType, ProposalType
from model.types.proposals import ProposalsEffect, new_proposal
from model.types.reaction_time import ReactionTime
from model.types.scenario import Scenario
from model.utils.seed import initialize_seed
from specs.tests.accounting_test import base_int_strategy, ethereum_address_strategy
from specs.time_manager import TimeManager
from specs.utils import ether_base

sys.modules["model.actors.utils"].IS_NUMBA = True
MAX_HEALTH = 100
MIN_HEALTH = 1


@st.composite
def float_number_strategy(draw):
    wei_value = draw(base_int_strategy())
    ether_value = wei_value / ether_base
    return ether_value


@st.composite
def actor_data(draw):
    n = draw(st.integers(min_value=1, max_value=100))
    addresses = draw(st.lists(ethereum_address_strategy(), min_size=n, max_size=n))
    stETH = draw(st.lists(float_number_strategy(), min_size=n, max_size=n))
    wstETH = draw(st.lists(float_number_strategy(), min_size=n, max_size=n))
    health = draw(st.lists(st.integers(min_value=MIN_HEALTH, max_value=MAX_HEALTH), min_size=n, max_size=n))
    ldo = draw(st.lists(st.integers(min_value=0, max_value=1), min_size=n, max_size=n))
    entities = draw(st.lists(st.sampled_from(["Contract", "Custody", "CEX", "Other"]), min_size=n, max_size=n))
    labels = draw(
        st.lists(st.sampled_from(["Whale", "Institutional", "Decentralized", "Other"]), min_size=n, max_size=n)
    )
    actor_types = draw(st.lists(st.sampled_from([ActorType.HonestActor.value]), min_size=n, max_size=n))
    reaction_time = draw(
        st.lists(
            st.sampled_from(
                [
                    ReactionTime.Normal.value,
                    ReactionTime.Quick.value,
                    ReactionTime.Slow.value,
                    ReactionTime.NoReaction.value,
                ]
            ),
            min_size=n,
            max_size=n,
        )
    )
    governance_participation = draw(
        st.lists(st.sampled_from([GovernanceParticipation.Normal.value]), min_size=n, max_size=n)
    )
    damage = draw(st.lists(st.integers(min_value=-MAX_HEALTH, max_value=MAX_HEALTH), min_size=n, max_size=n))

    return (
        addresses,
        stETH,
        wstETH,
        health,
        ldo,
        entities,
        labels,
        actor_types,
        reaction_time,
        governance_participation,
        damage,
    )


@given(actor_data())
def test_lock_and_unlock(actor_data):
    (
        addresses,
        stETH,
        wstETH,
        health,
        ldo,
        entities,
        labels,
        actor_types,
        reaction_time,
        governance_participation,
        _,
    ) = actor_data

    actors = Actors(
        address=np.array(addresses),
        stETH=np.array(stETH, dtype=np.float64),
        wstETH=np.array(wstETH, dtype=np.float64),
        health=np.array(health),
        actor_type=np.array(actor_types),
        reaction_time=np.array(reaction_time),
        ldo=np.array(ldo),
        entity=np.array(entities),
        label=np.array(labels),
        governance_participation=np.array(governance_participation),
    )

    time_manager = TimeManager()
    time_manager.initialize()

    lock_stETH_amounts = np.array(stETH, dtype=np.float64)
    lock_wstETH_amounts = np.array(wstETH, dtype=np.float64)
    mask = np.ones(len(stETH), dtype=bool)

    actors.lock_to_escrow(lock_stETH_amounts, lock_wstETH_amounts, time_manager.get_current_timestamp(), mask)

    np.testing.assert_array_equal(actors.stETH_locked, lock_stETH_amounts)
    np.testing.assert_array_equal(actors.wstETH_locked, lock_wstETH_amounts)

    actors.unlock_from_escrow(lock_stETH_amounts, lock_wstETH_amounts, time_manager.get_current_timestamp(), mask)

    np.testing.assert_array_equal(actors.stETH, stETH)
    np.testing.assert_array_equal(actors.wstETH, wstETH)


@given(actor_data())
def test_lock_to_escrow_with_excessive_amounts(actor_data):
    (
        addresses,
        stETH,
        wstETH,
        health,
        ldo,
        entities,
        labels,
        actor_types,
        reaction_time,
        governance_participation,
        _,
    ) = actor_data

    stETH_array = np.array(stETH, dtype=np.float64)
    wstETH_array = np.array(wstETH, dtype=np.float64)

    actors = Actors(
        address=np.array(addresses),
        stETH=stETH_array,
        wstETH=wstETH_array,
        health=np.array(health),
        actor_type=np.array(actor_types),
        reaction_time=np.array(reaction_time),
        ldo=np.array(ldo),
        entity=np.array(entities),
        label=np.array(labels),
        governance_participation=np.array(governance_participation),
    )

    time_manager = TimeManager()
    time_manager.initialize()

    lock_stETH_amounts = stETH_array + 1e-18
    lock_wstETH_amounts = wstETH_array
    mask = np.ones(len(stETH), dtype=bool)

    if not np.allclose(lock_stETH_amounts, stETH_array):
        with pytest.raises(NotEnoughActorStETHBalance):
            actors.lock_to_escrow(lock_stETH_amounts, lock_wstETH_amounts, time_manager.get_current_timestamp(), mask)

    lock_stETH_amounts = stETH_array
    lock_wstETH_amounts = wstETH_array + 1e-18

    if not np.allclose(lock_wstETH_amounts, wstETH_array):
        with pytest.raises(NotEnoughActorWstETHBalance):
            actors.lock_to_escrow(lock_stETH_amounts, lock_wstETH_amounts, time_manager.get_current_timestamp(), mask)


@given(actor_data())
def test_rebalance_to_stETH(actor_data):
    (
        addresses,
        stETH,
        wstETH,
        health,
        ldo,
        entities,
        labels,
        actor_types,
        reaction_time,
        governance_participation,
        _,
    ) = actor_data

    actors = Actors(
        address=np.array(addresses),
        stETH=np.array(stETH, dtype=np.float64),
        wstETH=np.array(wstETH, dtype=np.float64),
        health=np.array(health),
        actor_type=np.array(actor_types),
        reaction_time=np.array(reaction_time),
        ldo=np.array(ldo),
        entity=np.array(entities),
        label=np.array(labels),
        governance_participation=np.array(governance_participation),
    )

    time_manager = TimeManager()
    time_manager.initialize()

    lock_stETH_amounts = np.array(stETH, dtype=np.float64) - 1e-18
    lock_wstETH_amounts = np.array(wstETH, dtype=np.float64) - 1e-18

    mask = np.ones(len(stETH), dtype=bool)

    actors.lock_to_escrow(lock_stETH_amounts, lock_wstETH_amounts, time_manager.get_current_timestamp(), mask)

    stETH_balances_after_lock = np.array(stETH, dtype=np.float64) - lock_stETH_amounts
    wstETH_balances_after_lock = np.array(wstETH, dtype=np.float64) - lock_wstETH_amounts

    np.testing.assert_array_equal(actors.stETH, stETH_balances_after_lock)
    np.testing.assert_array_equal(actors.wstETH, wstETH_balances_after_lock)

    rebalance_stETH_amounts = lock_stETH_amounts
    rebalance_wstETH_amounts = lock_wstETH_amounts

    actors.rebalance_to_stETH(
        rebalance_stETH_amounts, rebalance_wstETH_amounts, time_manager.get_current_timestamp(), mask
    )

    expected_stETH = stETH_balances_after_lock + rebalance_stETH_amounts + rebalance_wstETH_amounts
    expected_stETH_locked = lock_stETH_amounts - rebalance_stETH_amounts
    expected_wstETH_locked = lock_wstETH_amounts - rebalance_wstETH_amounts

    np.testing.assert_allclose(actors.stETH, expected_stETH, rtol=1e-5, atol=1e-18)
    np.testing.assert_array_equal(actors.stETH_locked, expected_stETH_locked)
    np.testing.assert_array_equal(actors.wstETH_locked, expected_wstETH_locked)

    over_rebalance_stETH_amounts = lock_stETH_amounts + 1e-18
    over_rebalance_wstETH_amounts = lock_wstETH_amounts

    with pytest.raises(NotEnoughActorStETHBalance):
        actors.rebalance_to_stETH(
            over_rebalance_stETH_amounts, over_rebalance_wstETH_amounts, time_manager.get_current_timestamp(), mask
        )


@given(
    actor_data(),
    st.integers(min_value=1, max_value=10),
)
def test_update_actors_health(actor_data, seed):
    initialize_seed(seed)
    (
        addresses,
        stETH,
        wstETH,
        health,
        ldo,
        entities,
        labels,
        actor_types,
        reaction_time,
        governance_participation,
        damage,
    ) = actor_data

    actors = Actors(
        address=np.array(addresses),
        stETH=np.array(stETH, dtype=np.float64),
        wstETH=np.array(wstETH, dtype=np.float64),
        health=np.array(health),
        actor_type=np.array(actor_types),
        reaction_time=np.array(reaction_time),
        ldo=np.array(ldo),
        entity=np.array(entities),
        label=np.array(labels),
        governance_participation=np.array(governance_participation),
    )

    time_manager = TimeManager()
    time_manager.initialize()

    damage_array = np.array(damage)

    mask = np.ones(len(addresses), dtype=bool)

    prev_health = actors.health.copy()
    prev_total_damage = actors.total_damage.copy()
    prev_total_recovery = actors.total_recovery.copy()

    actors.update_actor_health(time_manager.get_current_timestamp(), damage_array, np.array(mask))

    adjusted_damage = damage_array.copy()
    mask1 = mask & (adjusted_damage > 0) & ((prev_health - adjusted_damage) < 0)
    adjusted_damage[mask1] = prev_health[mask1]

    mask2 = mask & (adjusted_damage > 0)

    expected_health = prev_health.copy()

    expected_health[mask2] -= adjusted_damage[mask2]

    mask3 = mask & (damage_array < 0)
    expected_health[mask3] += np.abs(damage_array[mask3])

    expected_health = np.clip(expected_health, 0, MAX_HEALTH)

    expected_total_damage = np.where(mask2, prev_total_damage + adjusted_damage, prev_total_damage)

    mask4 = mask & (damage_array < 0) & (prev_total_damage > 0)

    expected_total_recovery = np.where(mask4, prev_total_recovery + np.abs(damage_array), prev_total_recovery)

    np.testing.assert_array_equal(actors.health, expected_health)
    np.testing.assert_array_equal(actors.total_damage, expected_total_damage)
    np.testing.assert_array_equal(actors.total_recovery, expected_total_recovery)


@given(
    actor_data(), st.sampled_from([ProposalType.Danger, ProposalType.Negative]), st.sampled_from(list(ProposalSubType))
)
def test_simulate_proposal_effect(actor_data, proposal_type, sub_type):
    initialize_seed(1)
    (
        addresses,
        stETH,
        wstETH,
        health,
        ldo,
        entities,
        labels,
        actor_types,
        reaction_time,
        governance_participation,
        _,
    ) = actor_data

    stETH_array = np.array(stETH, dtype=np.float64)
    wstETH_array = np.array(wstETH, dtype=np.float64)

    actors = Actors(
        address=np.array(addresses),
        stETH=stETH_array,
        wstETH=wstETH_array,
        health=np.array(health, dtype=np.int64),
        actor_type=np.array(actor_types),
        reaction_time=np.array(reaction_time),
        ldo=np.array(ldo),
        entity=np.array(entities),
        label=np.array(labels),
        governance_participation=np.array(governance_participation),
    )

    time_manager = TimeManager()
    time_manager.initialize()

    proposal = new_proposal(
        timestep=10,
        id=1,
        scenario=Scenario.SingleAttack,
        proposer=addresses[0],
        proposal_type=proposal_type,
        sub_type=sub_type,
        attack_targets=set(),
    )

    actors.simulate_proposal_effect(proposal)
    contract_mask = entities == "Contract"

    if sub_type == ProposalSubType.NoEffect:
        np.testing.assert_allclose(actors.hypothetical_stETH, stETH_array, rtol=1e-5, atol=1e-18)
        np.testing.assert_allclose(actors.hypothetical_wstETH, wstETH_array, rtol=1e-5, atol=1e-18)

    elif sub_type == ProposalSubType.FundsStealing:
        expected_stETH = np.where(not contract_mask, actors.hypothetical_stETH, 0)
        expected_wstETH = np.where(not contract_mask, actors.hypothetical_wstETH, 0)

        np.testing.assert_allclose(
            actors.hypothetical_stETH,
            expected_stETH,
            rtol=1e-05,
            atol=1e-18,
            err_msg="Expected hypothetical_stETH to be 0 for non-contract entities.",
        )
        np.testing.assert_allclose(
            actors.hypothetical_wstETH,
            expected_wstETH,
            rtol=1e-05,
            atol=1e-18,
            err_msg="Expected hypothetical_stETH to be 0 for non-contract entities.",
        )

    elif sub_type == ProposalSubType.Hack:
        np.testing.assert_allclose(
            actors.hypothetical_stETH[contract_mask],
            0,
            rtol=1e-05,
            atol=1e-18,
            err_msg="Expected hypothetical_stETH to be 0 for contract entities.",
        )
        np.testing.assert_allclose(
            actors.hypothetical_wstETH[contract_mask],
            0,
            rtol=1e-05,
            atol=1e-18,
            err_msg="Expected hypothetical_wstETH to be 0 for contract entities.",
        )

    actors.after_simulate_proposal_effect()

    if sub_type == ProposalSubType.FundsStealing:
        expected_health = np.where(not contract_mask, actors.health, 0)
        np.testing.assert_array_equal(actors.health, expected_health)

    elif sub_type == ProposalSubType.Hack:
        expected_health = np.where(not contract_mask, actors.health, 0)
        np.testing.assert_array_equal(actors.health, expected_health)

    actors.reset_proposal_effect()

    np.testing.assert_allclose(
        actors.hypothetical_stETH,
        stETH_array,
        rtol=1e-05,
        atol=1e-08,
        err_msg="Expected hypothetical_stETH to be 0 for non-contract entities.",
    )
    np.testing.assert_allclose(
        actors.hypothetical_wstETH,
        wstETH_array,
        rtol=1e-05,
        atol=1e-08,
        err_msg="Expected hypothetical_stETH to be 0 for non-contract entities.",
    )

    actors.after_reset_proposal_effect()
    np.testing.assert_array_equal(actors.health, np.array(health))


@given(
    actor_data(), st.sampled_from([ProposalType.Danger, ProposalType.Negative]), st.sampled_from(list(ProposalSubType))
)
def test_apply_proposal_damage(actor_data, proposal_type, sub_type):
    initialize_seed(1)
    (
        addresses,
        stETH,
        wstETH,
        health,
        ldo,
        entities,
        labels,
        actor_types,
        reaction_time,
        governance_participation,
        _,
    ) = actor_data

    stETH_array = np.array(stETH, dtype=np.float64)
    wstETH_array = np.array(wstETH, dtype=np.float64)

    actors = Actors(
        address=np.array(addresses),
        stETH=stETH_array,
        wstETH=wstETH_array,
        health=np.array(health, dtype=np.int64),
        actor_type=np.array(actor_types),
        reaction_time=np.array(reaction_time),
        ldo=np.array(ldo),
        entity=np.array(entities),
        label=np.array(labels),
        governance_participation=np.array(governance_participation),
    )

    time_manager = TimeManager()
    time_manager.initialize()

    proposal_effect: ProposalsEffect = ProposalsEffect()
    proposal_effect.add_effect("Decentralized", 0)
    proposal_effect.add_effect("Whale", 10)
    proposal_effect.add_effect("Institutional", 35)

    proposal = new_proposal(
        timestep=10,
        id=1,
        scenario=Scenario.SingleAttack,
        proposer=addresses[0],
        proposal_type=proposal_type,
        sub_type=sub_type,
        attack_targets=set(),
        effects=proposal_effect,
    )

    expected_health = actors.health.copy()
    damage_array = np.repeat(proposal.damage, len(addresses)).astype(np.int16)

    actors.apply_proposal_damage(proposal, True)

    for label, label_damage in proposal.effects.effects.items():
        if label_damage != 0:
            damage_array[actors.label == label] = label_damage

    expected_health -= damage_array
    expected_health = np.clip(expected_health, 0, MAX_HEALTH)

    np.testing.assert_array_equal(actors.health, expected_health)

# import pytest
# from hypothesis import given
# from hypothesis import strategies as st

# from model.actors.actor import BaseActor
# from model.actors.errors import NotEnoughActorStETHBalance, NotEnoughActorWstETHBalance
# from model.types.escrow import ActorLockAmounts
# from model.types.governance_participation import GovernanceParticipation
# from model.types.proposal_type import ProposalSubType, ProposalType
# from model.types.proposals import new_proposal
# from model.types.reaction_time import ReactionTime
# from model.types.scenario import Scenario
# from model.utils.seed import initialize_seed
# from specs.tests.accounting_test import base_int_strategy, ethereum_address_strategy
# from specs.time_manager import TimeManager


# @given(
#     id=base_int_strategy(),
#     actor_address=ethereum_address_strategy(),
#     stETH_amount=base_int_strategy(),
#     wstETH_amount=base_int_strategy(),
#     health=st.integers(min_value=1, max_value=100),
# )
# def test_initialize(id: int, actor_address: str, stETH_amount: int, wstETH_amount: int, health: int):
#     time_manager = TimeManager()
#     time_manager.initialize()

#     base_actor = BaseActor()
#     base_actor.initialize(
#         id=id,
#         entity="Other",
#         address=actor_address,
#         health=health,
#         ldo=0,
#         stETH=stETH_amount,
#         wstETH=wstETH_amount,
#         reaction_time=ReactionTime.Quick,
#         governance_participation=GovernanceParticipation.Normal,
#     )

#     assert base_actor.id == id
#     assert base_actor.entity == "Other"
#     assert base_actor.address == actor_address
#     assert base_actor.health == health
#     assert base_actor.initial_health == health
#     assert base_actor.ldo_balance == 0

#     assert base_actor.st_eth_balance == stETH_amount
#     assert base_actor.initial_st_eth_balance == stETH_amount
#     assert base_actor.hypothetical_stETH_balance == stETH_amount

#     assert base_actor.wstETH_balance == wstETH_amount
#     assert base_actor.initial_wstETH_balance == wstETH_amount
#     assert base_actor.hypothetical_wstETH_balance == wstETH_amount

#     assert base_actor.reaction_time == ReactionTime.Quick
#     assert base_actor.governance_participation == GovernanceParticipation.Normal


# @given(
#     id=base_int_strategy(),
#     actor_address=ethereum_address_strategy(),
#     stETH_amount=base_int_strategy(),
#     wstETH_amount=base_int_strategy(),
#     health=st.integers(min_value=1, max_value=100),
#     damages=st.lists(st.floats(min_value=-100, max_value=100), min_size=1, max_size=10),
#     seed=st.integers(min_value=1, max_value=10),
# )
# def test_update_actor_health(
#     id: int, actor_address: str, stETH_amount: int, wstETH_amount: int, health: int, damages: list, seed: int
# ):
#     initialize_seed(seed)
#     time_manager = TimeManager()
#     time_manager.initialize()

#     base_actor = BaseActor()
#     base_actor.initialize(
#         id=id,
#         entity="Other",
#         address=actor_address,
#         health=health,
#         ldo=0,
#         stETH=stETH_amount,
#         wstETH=wstETH_amount,
#         reaction_time=ReactionTime.Quick,
#         governance_participation=GovernanceParticipation.Normal,
#     )

#     total_damage = 0
#     total_recovery = 0

#     for damage in damages:
#         previous_health = base_actor.health
#         base_actor.update_actor_health(time_manager, damage)

#         assert base_actor.health >= 0
#         assert base_actor.health <= 100

#         if damage > 0:
#             if previous_health - damage < 0:
#                 total_damage += previous_health
#             else:
#                 total_damage += damage

#             assert base_actor.total_damage == total_damage
#             assert base_actor.health == max(0, previous_health - damage)

#         elif damage < 0:
#             if base_actor.total_damage > 0:
#                 if previous_health + abs(damage) > 100:
#                     recovery_amount = 100 - previous_health
#                 else:
#                     recovery_amount = abs(damage)

#                 total_recovery = min(total_recovery + recovery_amount, total_damage)

#                 assert base_actor.total_recovery == total_recovery
#                 assert base_actor.health == min(100, previous_health + abs(damage))
#             else:
#                 assert base_actor.total_recovery == 0
#                 assert base_actor.health == min(100, previous_health + abs(damage))

#         if damage > 0 and previous_health - damage < 0:
#             assert base_actor.health == 0
#         elif damage < 0 and previous_health + abs(damage) > 100:
#             assert base_actor.health == 100

#     assert base_actor.total_recovery <= base_actor.total_damage


# @given(
#     id=base_int_strategy(),
#     actor_address=ethereum_address_strategy(),
#     stETH_amount=base_int_strategy(),
#     wstETH_amount=base_int_strategy(),
#     health=st.integers(min_value=1, max_value=100),
#     seed=st.integers(min_value=1, max_value=10),
#     stETH_lock=base_int_strategy(),
#     wstETH_lock=base_int_strategy(),
# )
# def test_lock_to_escrow(
#     id: int,
#     actor_address: str,
#     stETH_amount: int,
#     wstETH_amount: int,
#     health: int,
#     seed: int,
#     stETH_lock: int,
#     wstETH_lock: int,
# ):
#     initialize_seed(seed)
#     time_manager = TimeManager()
#     time_manager.initialize()
#     time = time_manager.get_current_timestamp()

#     base_actor = BaseActor()
#     base_actor.initialize(
#         id=id,
#         entity="Other",
#         address=actor_address,
#         health=health,
#         ldo=0,
#         stETH=stETH_amount,
#         wstETH=wstETH_amount,
#         reaction_time=ReactionTime.Quick,
#         governance_participation=GovernanceParticipation.Normal,
#     )

#     amounts = ActorLockAmounts(stETH_amount=stETH_lock, wstETH_amount=wstETH_lock)

#     if base_actor.st_eth_balance < stETH_lock:
#         with pytest.raises(NotEnoughActorStETHBalance):
#             base_actor.lock_to_escrow(amounts, time_manager)
#     elif base_actor.wstETH_balance < wstETH_lock:
#         with pytest.raises(NotEnoughActorWstETHBalance):
#             base_actor.lock_to_escrow(amounts, time_manager)
#     else:
#         base_actor.lock_to_escrow(amounts, time_manager)
#         assert base_actor.st_eth_balance == stETH_amount - stETH_lock
#         assert base_actor.st_eth_locked == stETH_lock
#         assert base_actor.wstETH_balance == wstETH_amount - wstETH_lock
#         assert base_actor.wstETH_locked == wstETH_lock
#         assert base_actor.last_locked_tx_timestamp == time


# @given(
#     id=base_int_strategy(),
#     actor_address=ethereum_address_strategy(),
#     stETH_amount=base_int_strategy(),
#     wstETH_amount=base_int_strategy(),
#     health=st.integers(min_value=1, max_value=100),
#     seed=st.integers(min_value=1, max_value=10),
#     stETH_lock=base_int_strategy(),
#     wstETH_lock=base_int_strategy(),
# )
# def test_unlock_to_escrow(
#     id: int,
#     actor_address: str,
#     stETH_amount: int,
#     wstETH_amount: int,
#     health: int,
#     seed: int,
#     stETH_lock: int,
#     wstETH_lock: int,
# ):
#     initialize_seed(seed)
#     time_manager = TimeManager()
#     time_manager.initialize()
#     time = time_manager.get_current_timestamp()

#     base_actor = BaseActor()
#     base_actor.initialize(
#         id=id,
#         entity="Other",
#         address=actor_address,
#         health=health,
#         ldo=0,
#         stETH=stETH_amount,
#         wstETH=wstETH_amount,
#         reaction_time=ReactionTime.Quick,
#         governance_participation=GovernanceParticipation.Normal,
#     )

#     amounts = ActorLockAmounts(stETH_amount=stETH_lock, wstETH_amount=wstETH_lock)
#     unlock_amounts = ActorLockAmounts(stETH_amount=-amounts.stETH_amount, wstETH_amount=-amounts.wstETH_amount)

#     if base_actor.st_eth_locked < stETH_lock:
#         with pytest.raises(NotEnoughActorStETHBalance):
#             base_actor.unlock_from_escrow(unlock_amounts, time_manager)
#     elif base_actor.wstETH_locked < wstETH_lock:
#         with pytest.raises(NotEnoughActorWstETHBalance):
#             base_actor.unlock_from_escrow(unlock_amounts, time_manager)
#     else:
#         base_actor.lock_to_escrow(amounts, time_manager)
#         assert base_actor.st_eth_balance == stETH_amount - stETH_lock
#         assert base_actor.st_eth_locked == stETH_lock
#         assert base_actor.wstETH_balance == wstETH_amount - wstETH_lock
#         assert base_actor.wstETH_locked == wstETH_lock
#         assert base_actor.last_locked_tx_timestamp == time

#         base_actor.unlock_from_escrow(unlock_amounts, time_manager)
#         assert base_actor.st_eth_balance == stETH_amount
#         assert base_actor.st_eth_locked == 0
#         assert base_actor.wstETH_balance == wstETH_amount
#         assert base_actor.wstETH_locked == 0
#         assert base_actor.last_locked_tx_timestamp == time


# @given(
#     id=base_int_strategy(),
#     actor_address=ethereum_address_strategy(),
#     stETH_amount=base_int_strategy(),
#     wstETH_amount=base_int_strategy(),
#     health=st.integers(min_value=1, max_value=100),
#     seed=st.integers(min_value=1, max_value=10),
#     stETH_lock=base_int_strategy(),
#     wstETH_lock=base_int_strategy(),
# )
# def test_rebalance_to_stETH(
#     id: int,
#     actor_address: str,
#     stETH_amount: int,
#     wstETH_amount: int,
#     health: int,
#     seed: int,
#     stETH_lock: int,
#     wstETH_lock: int,
# ):
#     initialize_seed(seed)
#     time_manager = TimeManager()
#     time_manager.initialize()
#     time = time_manager.get_current_timestamp()

#     base_actor = BaseActor()
#     base_actor.initialize(
#         id=id,
#         entity="Other",
#         address=actor_address,
#         health=health,
#         ldo=0,
#         stETH=stETH_amount,
#         wstETH=wstETH_amount,
#         reaction_time=ReactionTime.Quick,
#         governance_participation=GovernanceParticipation.Normal,
#     )

#     amounts = ActorLockAmounts(stETH_amount=stETH_lock, wstETH_amount=wstETH_lock)
#     unlock_amounts = ActorLockAmounts(stETH_amount=-amounts.stETH_amount, wstETH_amount=-amounts.wstETH_amount)

#     if base_actor.st_eth_balance < stETH_lock:
#         with pytest.raises(NotEnoughActorStETHBalance):
#             base_actor.lock_to_escrow(amounts, time_manager)
#     elif base_actor.wstETH_balance < wstETH_lock:
#         with pytest.raises(NotEnoughActorWstETHBalance):
#             base_actor.lock_to_escrow(amounts, time_manager)
#     else:
#         base_actor.lock_to_escrow(amounts, time_manager)
#         assert base_actor.st_eth_balance == stETH_amount - stETH_lock
#         assert base_actor.st_eth_locked == stETH_lock
#         assert base_actor.wstETH_balance == wstETH_amount - wstETH_lock
#         assert base_actor.wstETH_locked == wstETH_lock
#         assert base_actor.last_locked_tx_timestamp == time

#         left_wstETH = wstETH_amount - wstETH_lock

#         base_actor.rebalance_to_stETH(unlock_amounts, time_manager)
#         assert base_actor.st_eth_balance == (stETH_amount + wstETH_lock)
#         assert base_actor.st_eth_locked == 0
#         assert base_actor.wstETH_balance == left_wstETH
#         assert base_actor.wstETH_locked == 0
#         assert base_actor.last_locked_tx_timestamp == time


# @given(
#     id=base_int_strategy(),
#     actor_address=ethereum_address_strategy(),
#     stETH_amount=base_int_strategy(),
#     wstETH_amount=base_int_strategy(),
#     health=st.integers(min_value=1, max_value=100),
#     entity=st.sampled_from(["Contract", "Other"]),
#     proposal_type=st.sampled_from([ProposalType.Danger, ProposalType.Negative]),
#     sub_type=st.sampled_from(list(ProposalSubType)),
# )
# def test_proposal_effects(
#     id: int,
#     actor_address: str,
#     stETH_amount: int,
#     wstETH_amount: int,
#     health: int,
#     entity: str,
#     proposal_type: ProposalType,
#     sub_type: ProposalSubType,
# ):
#     initialize_seed(12412)
#     time_manager = TimeManager()
#     time_manager.initialize()

#     base_actor = BaseActor()
#     base_actor.initialize(
#         id=id,
#         entity=entity,
#         address=actor_address,
#         health=health,
#         ldo=0,
#         stETH=stETH_amount,
#         wstETH=wstETH_amount,
#         reaction_time=ReactionTime.Quick,
#         governance_participation=GovernanceParticipation.Normal,
#     )

#     proposal = new_proposal(
#         timestep=10,
#         id=1,
#         scenario=Scenario.SingleAttack,
#         proposer=actor_address,
#         proposal_type=proposal_type,
#         sub_type=sub_type,
#         attack_targets={actor_address},
#     )

#     base_actor.simulate_proposal_effect(proposal)

#     if sub_type == ProposalSubType.NoEffect:
#         assert base_actor.hypothetical_stETH_balance == stETH_amount
#         assert base_actor.hypothetical_wstETH_balance == wstETH_amount
#     elif sub_type == ProposalSubType.FundsStealing and entity == "Other":
#         assert base_actor.hypothetical_stETH_balance == 0
#         assert base_actor.hypothetical_wstETH_balance == 0
#     elif sub_type == ProposalSubType.Hack and entity == "Contract":
#         assert base_actor.hypothetical_stETH_balance == 0
#         assert base_actor.hypothetical_wstETH_balance == 0

#     base_actor.after_simulate_proposal_effect()

#     if sub_type == ProposalSubType.FundsStealing and entity == "Other":
#         assert base_actor.health == 0
#     elif sub_type == ProposalType.Hack and entity == "Contract":
#         assert base_actor.health == 0

#     base_actor.reset_proposal_effect()
#     assert base_actor.hypothetical_stETH_balance == stETH_amount
#     assert base_actor.hypothetical_wstETH_balance == wstETH_amount

#     base_actor.after_reset_proposal_effect()
#     assert base_actor.health == health

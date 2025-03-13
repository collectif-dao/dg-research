# from hypothesis import assume, given
# from hypothesis import strategies as st

# from model.actors.token_holders.stETH_holder_actor import StETHHolderActor
# from model.types.escrow import ActorLockAmounts
# from model.types.governance_participation import GovernanceParticipation
# from model.types.proposal_type import ProposalSubType, ProposalType
# from model.types.proposals import Proposal
# from model.types.reaction_time import ReactionTime
# from model.types.scenario import Scenario
# from model.utils.seed import initialize_seed
# from specs.dual_governance import DualGovernance
# from specs.dual_governance.proposals import ExecutorCall
# from specs.lido import Lido
# from specs.tests.accounting_test import base_int_strategy, ethereum_address_strategy
# from specs.tests.utils import sample_stETH_total_supply, test_escrow_address
# from specs.time_manager import TimeManager
# from specs.types.address import Address
# from specs.types.timestamp import Timestamp


# @given(
#     actor_address=ethereum_address_strategy(),
#     stETH_amount=base_int_strategy(),
#     wstETH_amount=base_int_strategy(),
#     health=st.integers(min_value=1, max_value=100),
#     damages=st.lists(st.floats(min_value=-100, max_value=100), min_size=1, max_size=10),
#     entity=st.sampled_from(["Contract", "Other"]),
#     proposal_type=st.sampled_from([ProposalType.Danger, ProposalType.Negative]),
#     sub_type=st.sampled_from(list(ProposalSubType)),
# )
# def test_honest_actor_lock_unlock(
#     actor_address: str,
#     stETH_amount: int,
#     wstETH_amount: int,
#     health: int,
#     damages: list[float],
#     entity: str,
#     proposal_type: ProposalType,
#     sub_type: ProposalSubType,
# ):
#     assume(actor_address != Address.ZERO)
#     initialize_seed(421)
#     time_manager = TimeManager()
#     time_manager.initialize()
#     sub_step = 5
#     scenario: Scenario = Scenario.HappyPath

#     lido = Lido()
#     lido.initialize(time_manager, Address.wstETH)
#     lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
#     lido.set_buffered_ether(sample_stETH_total_supply)

#     dual_governance = DualGovernance()
#     dual_governance.initialize(test_escrow_address, time_manager, lido)

#     honest_actor = StETHHolderActor()
#     honest_actor.initialize(
#         id=1,
#         entity=entity,
#         address=actor_address,
#         health=health,
#         ldo=0,
#         stETH=stETH_amount,
#         wstETH=wstETH_amount,
#         reaction_time=ReactionTime.Quick,
#         governance_participation=GovernanceParticipation.Normal,
#     )

#     if honest_actor.st_eth_balance > 0:
#         buffered_ether = lido.get_buffered_ether()
#         lido._mint_shares(honest_actor.address, honest_actor.st_eth_balance)
#         lido.set_buffered_ether(buffered_ether + honest_actor.st_eth_balance)

#     if honest_actor.wstETH_balance > 0:
#         buffered_ether = lido.get_buffered_ether()
#         lido._mint_shares(honest_actor.address, honest_actor.wstETH_balance)
#         lido.set_buffered_ether(buffered_ether + honest_actor.wstETH_balance)
#         lido.approve(honest_actor.address, Address.wstETH, honest_actor.wstETH_balance)
#         lido.wrap(honest_actor.address, honest_actor.wstETH_balance)

#     timestep = 1
#     proposals: list[Proposal] = []
#     locked: bool = False
#     unlocked: bool = False

#     for damage in damages:
#         new_proposal_id = (
#             dual_governance.timelock.proposals.count() + dual_governance.timelock.proposals.proposal_id_offset
#         )

#         proposal = Proposal(
#             id=new_proposal_id,
#             timestep=timestep,
#             damage=damage,
#             proposer=actor_address,
#             proposal_type=proposal_type,
#             sub_type=sub_type,
#             attack_targets={actor_address},
#         )
#         proposals.append(proposal)

#         dual_governance.submit_proposal(proposal.proposer, [ExecutorCall("", "", [])])

#         honest_actor.update_actor_health(time_manager, damage)

#         time_manager.shift_current_timestamp(Timestamp.from_uint256(sub_step))
#         timestep += 1

#         if honest_actor.health > 0 and honest_actor.total_damage == 0 and honest_actor.total_recovery == 0:
#             lock_amount = honest_actor.calculate_lock_amount(scenario, dual_governance, proposals)

#             assert lock_amount[0] == 0
#             assert lock_amount[1] == 0
#         elif honest_actor.health == 0 and honest_actor.total_damage > 0:
#             time_manager.shift_current_timestamp(Timestamp.from_uint256(honest_actor.reaction_delay))
#             lock_amount = honest_actor.calculate_lock_amount(scenario, dual_governance, proposals)

#             if not locked:
#                 assert lock_amount[0] == stETH_amount
#                 assert lock_amount[1] == wstETH_amount

#                 lock_amounts = ActorLockAmounts(stETH_amount=lock_amount[0], wstETH_amount=lock_amount[1])
#                 honest_actor.lock_to_escrow(lock_amounts, time_manager)
#                 locked = True
#                 unlocked = False

#                 assert honest_actor.st_eth_balance == 0
#                 assert honest_actor.st_eth_locked == stETH_amount
#                 assert honest_actor.wstETH_balance == 0
#                 assert honest_actor.wstETH_locked == wstETH_amount
#                 assert honest_actor.last_locked_tx_timestamp == time_manager.get_current_timestamp()

#         elif honest_actor.total_recovery > 0 and honest_actor.health > 0 and locked:
#             delta_time = (
#                 honest_actor.recovery_time + honest_actor.reaction_delay
#             ) - dual_governance.time_manager.get_current_timestamp()
#             time_manager.shift_current_timestamp(Timestamp.from_uint256(delta_time))
#             unlock_amount = honest_actor.calculate_lock_amount(scenario, dual_governance, proposals)

#             if not unlocked:
#                 assert unlock_amount[0] == -stETH_amount
#                 assert unlock_amount[1] == -wstETH_amount

#                 unlock_amounts = ActorLockAmounts(stETH_amount=unlock_amount[0], wstETH_amount=unlock_amount[1])
#                 honest_actor.unlock_from_escrow(unlock_amounts, time_manager)
#                 unlocked = True
#                 locked = False

#                 assert honest_actor.st_eth_balance == stETH_amount
#                 assert honest_actor.st_eth_locked == 0
#                 assert honest_actor.wstETH_balance == wstETH_amount
#                 assert honest_actor.wstETH_locked == 0
#                 assert honest_actor.last_locked_tx_timestamp == time_manager.get_current_timestamp()

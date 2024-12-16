from typing import List

import numpy as np

from model.parts.actors import ActorReaction
from specs.dual_governance import DualGovernance
from specs.dual_governance.state import State
from specs.lido import Lido
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp


# Behaviors
def add_deltatime_to_dg(params, substep, state_history, prev_state):
    delta = params["timedelta_tick"]
    return {"timedelta_tick": delta}


# Mechanisms
def update_escrow(params, substep, state_history, prev_state, policy_input):
    delta_staked_by_agent: List[np.ndarray, np.ndarray, np.ndarray] = policy_input["agent_delta_staked"]
    reactions: np.ndarray = policy_input["actor_reactions"]
    dual_governance: DualGovernance = prev_state["dual_governance"]

    for actor_address, stETH_amount, wstETH_amount, reaction in zip(*delta_staked_by_agent, reactions):
        if stETH_amount == 0 and wstETH_amount == 0:
            continue

        if stETH_amount > 0:
            dual_governance.state.signalling_escrow.lido.approve(
                actor_address, dual_governance.state.signalling_escrow.address, stETH_amount
            )
            dual_governance.state.signalling_escrow.lock_stETH(actor_address, stETH_amount)

        if wstETH_amount > 0:
            dual_governance.state.signalling_escrow.lido.wstETH.approve(
                actor_address, dual_governance.state.signalling_escrow.address, wstETH_amount
            )
            dual_governance.state.signalling_escrow.lock_wstETH(actor_address, wstETH_amount)

        if stETH_amount < 0 and wstETH_amount == 0:
            lock_time = int(dual_governance.state.signalling_escrow.signaling_escrow_min_lock_time.total_seconds())
            assetsUnlockAllowedAfter = dual_governance.state.signalling_escrow.accounting.state.assets[
                actor_address
            ].lastAssetsLockTimestamp + Timestamp.from_uint256(lock_time)

            if (
                dual_governance.state.signalling_escrow.time_manager.get_current_timestamp_value()
                <= assetsUnlockAllowedAfter
            ):
                continue
            else:
                dual_governance.state.signalling_escrow.unlock_stETH(actor_address)

        if wstETH_amount < 0 and stETH_amount == 0:
            lock_time = int(dual_governance.state.signalling_escrow.signaling_escrow_min_lock_time.total_seconds())

            assetsUnlockAllowedAfter = dual_governance.state.signalling_escrow.accounting.state.assets[
                actor_address
            ].lastAssetsLockTimestamp + Timestamp.from_uint256(lock_time)

            if (
                dual_governance.state.signalling_escrow.time_manager.get_current_timestamp_value()
                <= assetsUnlockAllowedAfter
            ):
                continue
            else:
                dual_governance.state.signalling_escrow.unlock_wstETH(actor_address)

        if wstETH_amount < 0 and stETH_amount < 0:
            lock_time = int(dual_governance.state.signalling_escrow.signaling_escrow_min_lock_time.total_seconds())
            assetsUnlockAllowedAfter = dual_governance.state.signalling_escrow.accounting.state.assets[
                actor_address
            ].lastAssetsLockTimestamp + Timestamp.from_uint256(lock_time)

            if (
                dual_governance.state.signalling_escrow.time_manager.get_current_timestamp_value()
                <= assetsUnlockAllowedAfter
            ):
                continue
            else:
                dual_governance.state.signalling_escrow.unlock_stETH(actor_address)

        if reaction == ActorReaction.Quit.value:
            ## TODO: implement
            pass

    return ("dual_governance", dual_governance)


def update_dg_time_manager(params, substep, state_history, prev_state, policy_input):
    delta = policy_input["timedelta_tick"]
    time_manager: TimeManager = prev_state["time_manager"]
    dual_governance: DualGovernance = prev_state["dual_governance"]
    time_manager.shift_current_time(delta)

    rage_quit_support = dual_governance.state.signalling_escrow.get_rage_quit_support()
    state = dual_governance.get_current_state()

    if state == State.VetoSignalling and dual_governance.state._is_veto_signalling_reactivation_duration_passed():
        dual_governance.activate_next_state()  ## should transition to VetoSignallingDeactivation state

    if (
        state == State.VetoSignalling
        and dual_governance.state._is_second_seal_rage_quit_support_crossed(rage_quit_support)
        and dual_governance.state._is_dynamic_timelock_duration_passed(rage_quit_support)
    ):
        dual_governance.activate_next_state()  ## should transition to RageQuit state

    if (
        state == State.VetoSignallingDeactivation
        and dual_governance.state._is_veto_signalling_deactivation_max_duration_passed()
    ):
        dual_governance.activate_next_state()  ## should transition to VetoCooldown state

    if state == State.VetoCooldown and dual_governance.state._is_veto_cooldown_duration_passed():
        dual_governance.activate_next_state()  ## should transition to Normal or VetoSignalling state

    if state == State.RageQuit:
        if dual_governance.state.rage_quit_escrow is not None:
            is_rage_quit_finalized = dual_governance.state.rage_quit_escrow.is_rage_quit_finalized()

            if is_rage_quit_finalized:
                dual_governance.activate_next_state()
                print("✓ Rage quit finalized, stopping")

            escrow = dual_governance.state.rage_quit_escrow
            lido: Lido = prev_state["lido"]

            if lido.balance_of(escrow.address) > 0:
                requested_amounts = escrow.batches_queue.calc_request_amounts(
                    escrow.min_withdrawal_request_amount,
                    escrow.max_withdrawal_request_amount,
                    lido.balance_of(escrow.address),
                )

                total_requests = len(requested_amounts)

                # if total_requests == 0:
                #     return ("dual_governance", dual_governance)

                if total_requests > escrow.max_withdrawal_batch_size:
                    remaining_requests = total_requests - escrow.max_withdrawal_batch_size
                    if remaining_requests < escrow.min_withdrawal_batch_size:
                        first_batch_size = total_requests - escrow.min_withdrawal_batch_size
                        escrow.request_next_withdrawals_batch(first_batch_size)
                    else:
                        escrow.request_next_withdrawals_batch(escrow.max_withdrawal_batch_size)
                elif total_requests > 0:
                    escrow.request_next_withdrawals_batch(total_requests)

                unstETH_ids = escrow.withdrawal_queue.get_withdrawal_requests(escrow.address)

                last_finalized_request = escrow.withdrawal_queue.queue[
                    escrow.withdrawal_queue.last_finalized_request_id
                ]
                request_to_finalize = escrow.withdrawal_queue.queue[unstETH_ids[-1]]

                steth_to_finalize = request_to_finalize.cumulative_stETH - last_finalized_request.cumulative_stETH

                escrow.withdrawal_queue.finalize(unstETH_ids[-1], steth_to_finalize, 1 * 10**27)
                escrow.claim_next_withdrawals_batch(len(unstETH_ids))

                buffered_ether = lido.get_buffered_ether()
                new_buffered_ether = buffered_ether - steth_to_finalize

                lido.set_buffered_ether(new_buffered_ether)
                lido._burn_shares(escrow.withdrawal_queue.address, steth_to_finalize)

                if (
                    len(requested_amounts) > 0
                    and len(requested_amounts) < escrow.max_withdrawal_batch_size
                    and escrow.batches_queue.is_all_unstETH_claimed()
                ):
                    escrow.batches_queue.close()
                    escrow.start_rage_quit_extension_delay()

    return ("dual_governance", dual_governance)

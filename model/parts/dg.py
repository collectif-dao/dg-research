from datetime import date
from typing import List

import numpy as np

from model.parts.actors import ActorReaction
from model.utils.numbers import max_withdrawal_per_day
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


def update_dual_governance_state(params, substep, state_history, prev_state, policy_input):
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

            if lido.balance_of(escrow.address) > 0 and not escrow.batches_queue.is_closed():
                requested_amounts = escrow.batches_queue.calc_request_amounts(
                    escrow.min_withdrawal_request_amount,
                    escrow.max_withdrawal_request_amount,
                    lido.balance_of(escrow.address),
                )

                total_requests = len(requested_amounts)

                if total_requests > 0:
                    if total_requests > escrow.max_withdrawal_batch_size:
                        remaining_requests = total_requests - escrow.max_withdrawal_batch_size
                        if remaining_requests < escrow.min_withdrawal_batch_size:
                            first_batch_size = total_requests - escrow.min_withdrawal_batch_size
                            escrow.request_next_withdrawals_batch(first_batch_size)
                        else:
                            escrow.request_next_withdrawals_batch(escrow.max_withdrawal_batch_size)
                    elif total_requests >= escrow.min_withdrawal_batch_size:
                        escrow.request_next_withdrawals_batch(total_requests)

    return ("dual_governance", dual_governance)


def calculate_withdrawal_amounts(params, substep, state_history, prev_state):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    lido_exit_share: int = prev_state["lido_exit_share"]
    last_withdrawal_day: date = prev_state["last_withdrawal_day"]
    churn_rate: int = prev_state["churn_rate"]
    time_manager: TimeManager = prev_state["time_manager"]

    if dual_governance.state.rage_quit_escrow is None or dual_governance.get_current_state() != State.RageQuit:
        return {"withdrawal_data": None}

    escrow = dual_governance.state.rage_quit_escrow

    if len(escrow.withdrawal_queue.requests_by_owner) == 0:
        return {"withdrawal_data": None}

    unstETH_ids = escrow.withdrawal_queue.get_withdrawal_requests(escrow.address)
    if not unstETH_ids:
        return {"withdrawal_data": None}

    current_day = time_manager.get_current_time().date()

    if last_withdrawal_day == current_day:
        return {"withdrawal_data": None}

    daily_withdrawal_limit = max_withdrawal_per_day(churn_rate, lido_exit_share)
    last_finalized_request = escrow.withdrawal_queue.queue[escrow.withdrawal_queue.last_finalized_request_id]

    withdrawals_to_process = []
    total_to_finalize = 0

    for unstETH_id in unstETH_ids:
        if unstETH_id <= escrow.withdrawal_queue.last_finalized_request_id:
            continue

        if total_to_finalize >= daily_withdrawal_limit:
            break

        request_to_finalize = escrow.withdrawal_queue.queue[unstETH_id]
        request_amount = request_to_finalize.cumulative_stETH - last_finalized_request.cumulative_stETH

        if request_amount + total_to_finalize > daily_withdrawal_limit:
            break

        withdrawals_to_process.append({"unstETH_id": unstETH_id, "amount": request_amount})
        total_to_finalize += request_amount
        last_finalized_request = request_to_finalize

    return {
        "withdrawal_data": {
            "withdrawals": withdrawals_to_process,
            "total_amount": total_to_finalize,
            "current_day": current_day,
        }
    }


def update_last_withdrawal_day(params, substep, state_history, prev_state, policy_input):
    withdrawal_data = policy_input["withdrawal_data"]

    if withdrawal_data is None or len(withdrawal_data["withdrawals"]) == 0:
        return ("last_withdrawal_day", prev_state["last_withdrawal_day"])

    return ("last_withdrawal_day", withdrawal_data["current_day"])


def process_withdrawals(params, substep, state_history, prev_state, policy_input):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    lido: Lido = prev_state["lido"]
    withdrawal_data = policy_input["withdrawal_data"]

    if withdrawal_data is None or len(withdrawal_data["withdrawals"]) == 0:
        return ("dual_governance", dual_governance)

    escrow = dual_governance.state.rage_quit_escrow

    escrow.withdrawal_queue.finalize(
        withdrawal_data["withdrawals"][-1]["unstETH_id"], withdrawal_data["total_amount"], 1 * 10**27
    )

    escrow.claim_next_withdrawals_batch(len(withdrawal_data["withdrawals"]))

    if withdrawal_data["total_amount"] > 0:
        buffered_ether = lido.get_buffered_ether()
        new_buffered_ether = buffered_ether - withdrawal_data["total_amount"]
        lido.set_buffered_ether(new_buffered_ether)
        lido._burn_shares(escrow.withdrawal_queue.address, withdrawal_data["total_amount"])

    if escrow.batches_queue.is_all_unstETH_claimed():
        escrow.batches_queue.close()
        escrow.start_rage_quit_extension_delay()

    return ("dual_governance", dual_governance)

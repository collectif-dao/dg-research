from typing import Dict

from model.types.escrow import ActorLockAmounts
from specs.dual_governance import DualGovernance
from specs.lido import Lido
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp


# Behaviors
def add_deltatime_to_dg(params, substep, state_history, prev_state):
    delta = params["timedelta_tick"]
    return {"timedelta_tick": delta}


# Mechanisms
def update_escrow(params, substep, state_history, prev_state, policy_input):
    delta_staked_by_agent: Dict[str, ActorLockAmounts] = policy_input["agent_delta_staked"]
    dual_governance: DualGovernance = prev_state["dual_governance"]

    for actor_address, delta_staked in delta_staked_by_agent.items():
        if delta_staked.stETH_amount == 0 and delta_staked.wstETH_amount == 0:
            continue

        if delta_staked.stETH_amount > 0:
            dual_governance.state.signalling_escrow.lido.approve(
                actor_address, dual_governance.state.signalling_escrow.address, delta_staked.stETH_amount
            )
            dual_governance.state.signalling_escrow.lock_stETH(actor_address, delta_staked.stETH_amount)

        if delta_staked.wstETH_amount > 0:
            dual_governance.state.signalling_escrow.lido.wstETH.approve(
                actor_address, dual_governance.state.signalling_escrow.address, delta_staked.wstETH_amount
            )
            dual_governance.state.signalling_escrow.lock_wstETH(actor_address, delta_staked.wstETH_amount)

        if delta_staked.stETH_amount < 0 and delta_staked.wstETH_amount == 0:
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

        if delta_staked.wstETH_amount < 0 and delta_staked.stETH_amount == 0:
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

        if delta_staked.wstETH_amount < 0 and delta_staked.stETH_amount < 0:
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
                print("rare case")

    return ("dual_governance", dual_governance)


def update_time_manager(params, substep, state_history, prev_state, policy_input):
    delta = policy_input["timedelta_tick"]
    time_manager: TimeManager = prev_state["time_manager"]
    time_manager.shift_current_time(delta)

    return ("time_manager", time_manager)


def update_dg_time_manager(params, substep, state_history, prev_state, policy_input):
    delta = policy_input["timedelta_tick"]
    dual_governance: DualGovernance = prev_state["dual_governance"]

    dual_governance.state.time_manager.shift_current_time(delta)
    # dual_governance.activate_next_state()
    return ("dual_governance", dual_governance)


def update_lido_time_manager(params, substep, state_history, prev_state, policy_input):
    delta = policy_input["timedelta_tick"]
    lido: Lido = prev_state["lido"]
    lido.time_manager.shift_current_time(delta)

    return ("lido", lido)

from .utils import *


# Behaviors
def add_deltatime_to_dg(params, substep, state_history, prev_state):
    delta = params["timedelta_tick"]
    return {"timedelta_tick": delta}


# Mechanisms
def update_escrow(params, substep, state_history, prev_state, policy_input):
    delta_staked_by_agent = policy_input["agent_delta_staked"]
    dg = prev_state["dg"]

    for agent, delta_staked in delta_staked_by_agent.items():
        dg.state.signalling_escrow.lock_stETH("0xc0ffee254729296a45a3885639AC7E10F9d54979", delta_staked)

    return ("dg", dg)


def update_time_manager(params, substep, state_history, prev_state, policy_input):
    delta = policy_input["timedelta_tick"]
    time_manager = prev_state["time_manager"]

    time_manager.shift_current_time(delta)

    return ("time_manager", time_manager)


def update_state(params, substep, state_history, prev_state, policy_input):
    delta = policy_input["timedelta_tick"]
    dg = prev_state["dg"]

    dg.time_manager.shift_current_time(delta)
    dg.state.time_manager.shift_current_time(delta)
    dg.state.signalling_escrow.time_manager.shift_current_time(delta)
    dg.state.signalling_escrow.accounting.time_manager.shift_current_time(delta)

    dg.activate_next_state()

    return ("dg", dg)

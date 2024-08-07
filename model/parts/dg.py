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
        if delta_staked > 0:
            dg.state.signalling_escrow.lock_stETH(agent, delta_staked)
        if delta_staked < 0:
            dg.state.signalling_escrow.unlock_stETH(agent)

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


def update_proposals_time(params, substep, state_history, prev_state, policy_input):
    delta = policy_input["timedelta_tick"]

    proposals = prev_state["proposals_new"]

    proposals.time_manager.shift_current_time(delta)

    return ("proposals_new", proposals)

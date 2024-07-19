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
        dg.signalling_escrow.stake_stETH(delta_staked)

    return ("dg", dg)


def update_state(params, substep, state_history, prev_state, policy_input):
    delta = policy_input["timedelta_tick"]
    dg = prev_state["dg"]

    dg.shift_current_time(delta)

    dg.activate_next_state()

    return ("dg", dg)

from .utils import *


# Behaviors
def stake_st(params, substep, state_history, prev_state):
    dg = prev_state["dg"]
    actors = prev_state["actors"]
    staked = {}
    for actor in actors:
        amount = actor.will_change_escrow(dg)
        if amount != 0:
            staked[actor.address] = amount

    return {"agent_delta_staked": staked}


# Mechanisms
def actor_stake(params, substep, state_history, prev_state, policy_input):
    delta_staked_by_agent = policy_input["agent_delta_staked"]
    actors = prev_state["actors"]

    for actor in actors:
        if actor.address in delta_staked_by_agent:
            if delta_staked_by_agent[actor.address] > 0:
                actor.stake_to_escrow(delta_staked_by_agent[actor.address])
            if delta_staked_by_agent[actor.address] < 0:
                actor.unstake_from_escrow(actor.st_eth_locked)

    return ("actors", actors)

import random

from .utils import *


# Behaviors
def stake_st(params, substep, state_history, prev_state):
    proposals = prev_state["proposals"]
    agents = prev_state["agents"]
    staked = {}
    for agent_label, agent_property in agents.items():
        if agent_property["st_amount"] <= 0:
            continue
        prob = random.random()
        for proposal_label, proposal_property in proposals.items():
            if proposal_property["prob"] * agent_property["prob"] > prob:
                staked[agent_label] = agent_property["st_amount"]
                break
    return {"agent_delta_staked": staked}


# Mechanisms
def agent_stake(params, substep, state_history, prev_state, policy_input):
    delta_staked_by_agent = policy_input["agent_delta_staked"]
    agents = prev_state["agents"]

    updated_agents = prev_state["agents"].copy()

    for agent, delta_staked in delta_staked_by_agent.items():
        updated_agents[agent]["st_amount"] -= delta_staked

    return ("agents", updated_agents)

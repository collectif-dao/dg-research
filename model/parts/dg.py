import numpy as np
from .utils import *


# Behaviors
def grow_food(params, substep, state_history, prev_state):
    """
    Increases the food supply in all sites, subject to an maximum.
    """
    regenerated_sites = calculate_increment(
        prev_state["sites"], params["food_growth_rate"], params["maximum_food_per_site"]
    )
    return {"update_food": regenerated_sites}


# Mechanisms
def update_escrow(params, substep, state_history, prev_state, policy_input):
    delta_staked_by_agent = policy_input['agent_delta_staked']
    escrow = prev_state['escrow']

    updated_escrow = prev_state['escrow']

    for agent, delta_staked in delta_staked_by_agent.items():
        if agent in escrow.staked:
            updated_escrow.staked[agent] += delta_staked
        else:
            updated_escrow.staked[agent] = delta_staked

    return ("escrow", updated_escrow)

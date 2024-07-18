from .utils import *

# Behaviors


# Mechanisms
def update_escrow(params, substep, state_history, prev_state, policy_input):
    delta_staked_by_agent = policy_input["agent_delta_staked"]
    escrow = prev_state["escrow"]

    updated_escrow = prev_state["escrow"]

    for agent, delta_staked in delta_staked_by_agent.items():
        updated_escrow.stake_stETH(delta_staked)

    return ("escrow", updated_escrow)

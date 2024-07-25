import random

from .parts.agents import *
from .parts.dg import *
from .parts.proposals import *


def initialize_seed(params, substep, state_history, prev_state):
    if prev_state["timestep"] == 0:
        random.seed(a=f'{prev_state["simulation"]}/{prev_state["subset"]}/{prev_state["run"]}')
    return {}


state_update_blocks = [
    {
        # proposals.py
        "policies": {"generate_proposal": generate_proposal},
        "variables": {"proposals": add_proposal},
    },
    {
        # proposals.py
        "policies": {"proposal_expire": proposal_expire},
        "variables": {"proposals": proposal_remove},
    },
    {
        # agents.py
        "policies": {"stake_st": stake_st},
        "variables": {"agents": agent_stake, "dg": update_escrow},
    },
    {
        # agents.py
        "policies": {"add_deltatime_to_dg": add_deltatime_to_dg},
        "variables": {"time_manager": update_time_manager, "dg": update_state},
    },
]

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
        "variables": {"dg": submit_proposal, "proposals_type": register_proposals_type},
    },
    {
        # proposals.py
        "policies": {"update_proposals": update_proposals},
        "variables": {
            "dg": shedule_and_execute_proposals,
        },
    },
    {
        # agents.py, dg.py
        "policies": {"stake_st": stake_st},
        "variables": {"actors": actor_stake, "dg": update_escrow},
    },
    {
        # dg.py
        "policies": {"add_deltatime_to_dg": add_deltatime_to_dg},
        "variables": {"time_manager": update_time_manager, "dg": update_state},
    },
]

from .parts.environment import *
from .parts.agents import *
import random


def initialize_seed(params, substep, state_history, prev_state):
    if prev_state["timestep"] == 0:
        random.seed(
            a=f'{prev_state["simulation"]}/{prev_state["subset"]}/{prev_state["run"]}'
        )
    return {}


state_update_blocks = [
    {
         # agents.py
         'policies': {
             'generate_proposal': generate_proposal
         },
         'variables': {
             'proposals': add_proposal
         }
    },
    {
         # agents.py
         'policies': {
             'proposal_expire': proposal_expire
         },
         'variables': {
             'proposals': proposal_remove
         }
    }
]

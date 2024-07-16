from .utils import *
import random
from uuid import uuid4


# Behaviors
def generate_proposal(params, substep, state_history, prev_state):
    if (random.random() > 0.95):
        proposal = new_proposal(prev_state['timestep'])
        return {'proposal_create': proposal}
    else:
        return {'proposal_create': None}

def proposal_expire(params, substep, state_history, prev_state):
    """
    Remove proposals which are expire.
    """
    proposals = prev_state['proposals']
    proposals_to_remove = []
    for proposal_label, proposal_properties in proposals.items():
        to_remove = prev_state['timestep'] - proposal_properties['timestep'] >= 10
        if to_remove:
            proposals_to_remove.append(proposal_label)
    return {'remove_proposals': proposals_to_remove}


# Mechanisms
def add_proposal(params, substep, state_history, prev_state, policy_input):
    updated_proposals = prev_state['proposals'].copy()
    if policy_input['proposal_create'] is not None:
        updated_proposals[uuid4()] = policy_input['proposal_create']
    return ('proposals', updated_proposals)

def proposal_remove(params, substep, state_history, prev_state, policy_input):
    proposals_to_remove = policy_input["remove_proposals"]
    surviving_proposals = {
        k: v for k, v in prev_state["proposals"].items() if k not in proposals_to_remove
    }
    return ("proposals", surviving_proposals)

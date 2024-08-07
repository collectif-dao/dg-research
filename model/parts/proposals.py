import random

from specs.dual_governance.proposals import ExecutorCall

from .utils import *


# Behaviors
def generate_proposal(params, substep, state_history, prev_state):
    if random.random() > 0.95:
        proposal = new_proposal(prev_state["timestep"])
        return {"proposal_create": proposal}
    else:
        return {"proposal_create": None}


def update_proposals(params, substep, state_history, prev_state):
    return {"update_proposals": None}


# Mechanisms


def submit_proposal(params, substep, state_history, prev_state, policy_input):
    dg = prev_state["dg"]

    if policy_input["proposal_create"] is not None and dg.state.is_proposals_creation_allowed():
        dg.submit_proposal("", [ExecutorCall("", "", [])])

    return ("dg", dg)


def shedule_and_execute_proposals(params, substep, state_history, prev_state, policy_input):
    dg = prev_state["dg"]

    i = 0
    for proposal in dg.timelock.proposals.state.proposals:
        try:
            dg.schedule_proposal(proposal.id)
        except Exception:
            i = 1

    for proposal in dg.timelock.proposals.state.proposals:
        try:
            dg.execute_proposal(proposal.id)
        except Exception:
            i = 1

    return ("dg", dg)

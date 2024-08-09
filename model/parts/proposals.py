import random

from specs.dual_governance.proposals import ExecutorCall

from .utils import *


# Behaviors
def generate_proposal(params, substep, state_history, prev_state):
    dg = prev_state["dg"]
    new_proposal_id = dg.timelock.proposals.count() + dg.timelock.proposals.proposal_id_offset
    if random.random() > 0.95:
        proposal = new_proposal(prev_state["timestep"], new_proposal_id)
        return {"proposal_create": proposal}
    else:
        return {"proposal_create": None}


def update_proposals(params, substep, state_history, prev_state):
    return {"update_proposals": None}


# Mechanisms


def submit_proposal(params, substep, state_history, prev_state, policy_input):
    dg = prev_state["dg"]
    proposal = policy_input["proposal_create"]

    if proposal is not None and dg.state.is_proposals_creation_allowed():
        dg.submit_proposal("", [ExecutorCall("", "", [])])

    return ("dg", dg)


def register_proposals_type(params, substep, state_history, prev_state, policy_input):
    dg = prev_state["dg"]
    proposals_type = prev_state["proposals_type"]
    proposal = policy_input["proposal_create"]

    if proposal is not None and dg.state.is_proposals_creation_allowed():
        proposals_type[proposal["id"]] = proposal["type"]

    return ("proposals_type", proposals_type)


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

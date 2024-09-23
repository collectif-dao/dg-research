from datetime import datetime, timedelta
from typing import List, Set

from model.sys_params import cancellation_delay_days
from model.types.proposal_type import ProposalGeneration
from model.types.proposals import Proposal, ProposalType, get_proposal_by_id, new_proposal
from model.types.scenario import Scenario
from model.utils.proposals import iterable_proposals
from model.utils.seed import get_rng
from specs.dual_governance import DualGovernance
from specs.dual_governance.proposals import ExecutorCall, ProposalStatus
from specs.dual_governance.state import State
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp


# Behaviors
def generate_proposal(params, substep, state_history, prev_state):
    dual_governance: DualGovernance = prev_state["dual_governance"]

    if not dual_governance.state.is_proposals_creation_allowed():
        return {"proposal_create": None}

    if (
        dual_governance.get_current_state() == State.VetoSignalling
        and dual_governance.state._is_veto_signalling_reactivation_duration_passed()
    ):
        return {"proposal_create": None}

    scenario: Scenario = prev_state["scenario"]
    non_initialized_proposals: List[Proposal] = prev_state["non_initialized_proposals"]
    proposal_generation: ProposalGeneration = prev_state["proposal_generation"]
    new_proposal_id = dual_governance.timelock.proposals.count() + dual_governance.timelock.proposals.proposal_id_offset

    if len(non_initialized_proposals) > 0:
        for proposal in non_initialized_proposals:
            if proposal.timestep == prev_state["timestep"]:
                proposal.id = new_proposal_id

                if prev_state["is_active_attack"]:
                    proposal = None

                return {"proposal_create": proposal}

    match proposal_generation:
        case ProposalGeneration.Random:
            rng = get_rng()
            if rng.random() > 0.99:
                proposer: str = ""
                if scenario in [Scenario.CoordinatedAttack, Scenario.SingleAttack, Scenario.SmartContractHack]:
                    proposer = rng.choice(tuple(prev_state["attackers"]))

                ## TODO: check duplicated proposals if attack status is active

                proposal = new_proposal(
                    prev_state["timestep"],
                    new_proposal_id,
                    proposer,
                    scenario,
                    prev_state["proposal_types"],
                    prev_state["proposal_subtypes"],
                )

                if prev_state["is_active_attack"]:
                    proposal = None
            else:
                proposal = None

        case ProposalGeneration.TargetedAttack:
            is_active_attack = prev_state["is_active_attack"]

            if is_active_attack:
                proposal = None
            else:
                attackers: Set[str] = prev_state["attackers"]
                active_attackers = len(attackers)

                if active_attackers <= 0:
                    proposal = None
                else:
                    rng = get_rng()
                    attacker = rng.choice(tuple(attackers))

                    proposal = new_proposal(
                        prev_state["timestep"],
                        new_proposal_id,
                        attacker,
                        scenario,
                        prev_state["proposal_types"],
                        prev_state["proposal_subtypes"],
                    )
                    print(proposal)

    return {"proposal_create": proposal}


def cancel_all_pending_proposals(params, substep, state_history, prev_state):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    proposals: List[Proposal] = prev_state["proposals"]
    time_manager: TimeManager = prev_state["time_manager"]

    is_active_veto_signalling, _, _, activated_at = dual_governance.state.get_veto_signalling_state()
    if is_active_veto_signalling and time_manager.get_current_timestamp_value() >= activated_at + Timestamp(
        timedelta(days=cancellation_delay_days).total_seconds()
    ):
        total_num_of_proposals = dual_governance.timelock.proposals.count()
        last_canceled_proposal = dual_governance.timelock.proposals.state.last_canceled_proposal_id

        if total_num_of_proposals == last_canceled_proposal:
            return {"cancel_all_pending_proposals": []}

        start_proposal_id = last_canceled_proposal + 1

        proposals_iterable = iterable_proposals(
            dual_governance.timelock.proposals.state.proposals,
            start_proposal_id,
            total_num_of_proposals - last_canceled_proposal,
        )

        canceled_proposals = []

        if proposals_iterable is not None:
            for proposal in proposals_iterable:
                timelock_proposal = dual_governance.timelock.proposals.get(proposal.id)

                if timelock_proposal.status != ProposalStatus.Executed:
                    model_proposal = get_proposal_by_id(proposals, timelock_proposal.id)

                    if (
                        model_proposal.proposal_type == ProposalType.Negative
                        or ProposalType.Danger
                        or ProposalType.Hack
                    ):
                        if timelock_proposal.id <= last_canceled_proposal:
                            continue
                        else:
                            if model_proposal.cancelable:
                                print(model_proposal)
                                canceled_proposals.append(timelock_proposal.id)

        return {"cancel_all_pending_proposals": canceled_proposals}

    return {"cancel_all_pending_proposals": []}


# Mechanisms


def submit_proposal(params, substep, state_history, prev_state, policy_input):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    proposal = policy_input["proposal_create"]

    if proposal is not None:
        print(
            "submitting proposal with ID",
            proposal.id,
            "at ",
            dual_governance.time_manager.get_current_time(),
        )
        print(proposal)
        dual_governance.submit_proposal("", [ExecutorCall("", "", [])])

    return ("dual_governance", dual_governance)


def activate_attack(params, substep, state_history, prev_state, policy_input):
    proposal: Proposal = policy_input["proposal_create"]

    if proposal is None:
        return ("is_active_attack", prev_state["is_active_attack"])

    if proposal.proposal_type in (ProposalType.Danger, ProposalType.Hack, ProposalType.Negative):
        return ("is_active_attack", True)

    return ("is_active_attack", False)


def deactivate_attack(params, substep, state_history, prev_state, policy_input):
    ## TODO: check all list of proposals and make sure that if one attacking proposal is in the list, still have active_attack state
    cancel_proposals = policy_input["cancel_all_pending_proposals"]

    if len(cancel_proposals) > 0:
        return ("is_active_attack", False)

    return ("is_active_attack", prev_state["is_active_attack"])


def register_proposal(params, substep, state_history, prev_state, policy_input):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    proposals = prev_state["proposals"]
    proposal = policy_input["proposal_create"]

    if proposal is not None and dual_governance.state.is_proposals_creation_allowed():
        proposals.append(proposal)

    return ("proposals", proposals)


def initialize_proposal(params, substep, state_history, prev_state, policy_input):
    non_initialized_proposals: List[Proposal] = prev_state["non_initialized_proposals"]
    proposal: Proposal = policy_input["proposal_create"]

    if proposal is not None and len(non_initialized_proposals) > 0:
        non_initialized_proposals = [
            non_initialized_proposal
            for non_initialized_proposal in non_initialized_proposals
            if not (
                non_initialized_proposal.timestep == proposal.timestep
                and non_initialized_proposal.damage == proposal.damage
                and non_initialized_proposal.attack_targets == proposal.attack_targets
                and non_initialized_proposal.proposal_type == proposal.proposal_type
                and non_initialized_proposal.sub_type == proposal.sub_type
            )
        ]

    return ("non_initialized_proposals", non_initialized_proposals)


def schedule_and_execute_proposals(params, substep, state_history, prev_state, policy_input):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    cancel_proposals = policy_input["cancel_all_pending_proposals"]

    if len(cancel_proposals) != 0:
        print("need to cancel proposals")
        print(cancel_proposals)
        dual_governance.cancel_all_pending_proposals()

    for proposal in dual_governance.timelock.proposals.state.proposals:
        if dual_governance.can_schedule(proposal.id) and dual_governance.state.can_schedule_proposal(
            proposal.submittedAt
        ):
            print(
                "scheduling proposal with ID",
                proposal.id,
                "at ",
                dual_governance.time_manager.get_current_time(),
                "that has been submitted at ",
                datetime.fromtimestamp(proposal.submittedAt.value),
            )
            dual_governance.schedule_proposal(proposal.id)

    for proposal in dual_governance.timelock.proposals.state.proposals:
        if dual_governance.can_execute(proposal.id):
            print(
                "executing proposal with ID",
                proposal.id,
                "at ",
                dual_governance.time_manager.get_current_time(),
                "that has been scheduled at ",
                datetime.fromtimestamp(proposal.scheduledAt.value),
                "and submitted at ",
                datetime.fromtimestamp(proposal.submittedAt.value),
            )

            dual_governance.execute_proposal(proposal.id)

    return ("dual_governance", dual_governance)

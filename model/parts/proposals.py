from datetime import timedelta
from typing import List, Set

from model.sys_params import cancellation_delay_days
from model.types.proposal_type import ProposalGeneration
from model.types.proposals import (Proposal, ProposalType, get_proposal_by_id,
                                   new_proposal)
from model.types.scenario import Scenario
from model.utils.proposals import iterable_proposals
from model.utils.proposals_queue import ProposalQueueManager
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
        return {"proposal_create": []}

    if (
        dual_governance.get_current_state() == State.VetoSignalling
        and dual_governance.state._is_veto_signalling_reactivation_duration_passed()
    ):
        return {"proposal_create": []}

    non_initialized_proposals: List[Proposal] = prev_state["non_initialized_proposals"]
    queue: ProposalQueueManager = prev_state["proposals_queue"]
    timestep: int = prev_state["timestep"]
    new_proposal_id = (
        dual_governance.timelock.proposals.count()
        + dual_governance.timelock.proposals.proposal_id_offset
        + queue.count()
    )
    proposals: List[Proposal] = []

    if len(non_initialized_proposals) > 0:
        created_proposal = False

        for proposal in non_initialized_proposals:
            if proposal.timestep == prev_state["timestep"]:
                proposal.id = new_proposal_id
                new_proposal_id += 1

                if proposal is not None:
                    queue.append_proposal(proposal)
                    created_proposal = True

        if created_proposal:
            proposals = queue.pop_proposals_for_registration(timestep)

        return {"proposal_create": proposals}

    proposal_generation: ProposalGeneration = prev_state["proposal_generation"]
    scenario: Scenario = prev_state["scenario"]
    proposal: Proposal | None = None

    if not prev_state["is_active_attack"]:
        match proposal_generation:
            case ProposalGeneration.Random:
                rng = get_rng()
                if rng.random() > 0.99:
                    proposer: str = ""
                    if scenario in [
                        Scenario.CoordinatedAttack,
                        Scenario.SingleAttack,
                        Scenario.SmartContractHack,
                        Scenario.VetoSignallingLoop,
                        Scenario.ConstantVetoSignallingLoop,
                    ]:
                        if len(prev_state["attackers"]) == 0:
                            proposer = ""
                        else:
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

            case ProposalGeneration.TargetedAttack:
                attackers: Set[str] = prev_state["attackers"]
                active_attackers = len(attackers)

                if active_attackers > 0:
                    rng = get_rng()
                    attacker = rng.choice(tuple(attackers))

                    if queue.count() == 0:
                        proposal = new_proposal(
                            prev_state["timestep"],
                            new_proposal_id,
                            attacker,
                            scenario,
                            prev_state["proposal_types"],
                            prev_state["proposal_subtypes"],
                        )

    if proposal is not None:
        queue.append_proposal(proposal)
    proposals = queue.pop_proposals_for_registration(timestep)

    return {"proposal_create": proposals}


def get_proposals_to_cancel(params, substep, state_history, prev_state):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    time_manager: TimeManager = prev_state["time_manager"]

    is_active_veto_signalling, _, _, activated_at = dual_governance.state.get_veto_signalling_state()
    cancellation_time = activated_at + Timestamp(timedelta(days=cancellation_delay_days).total_seconds())

    if not (is_active_veto_signalling and time_manager.get_current_timestamp_value() >= cancellation_time):
        return {"cancel_all_pending_proposals": []}

    total_proposals = dual_governance.timelock.proposals.count()
    last_canceled = dual_governance.timelock.proposals.state.last_canceled_proposal_id

    if total_proposals == last_canceled:
        return {"cancel_all_pending_proposals": []}

    proposals_iterable = iterable_proposals(
        dual_governance.timelock.proposals.state.proposals,
        last_canceled + 1,
        total_proposals - last_canceled,
    )

    if not proposals_iterable:
        return {"cancel_all_pending_proposals": []}

    scenario: Scenario = prev_state["scenario"]
    canceled_proposals = []

    for proposal in proposals_iterable:
        timelock_proposal = dual_governance.timelock.proposals.get(proposal.id)

        if timelock_proposal.status == ProposalStatus.Executed:
            continue

        model_proposal = get_proposal_by_id(prev_state["proposals"], timelock_proposal.id)

        if _should_cancel_proposal(scenario, model_proposal):
            if not model_proposal.cancelable:
                return {"cancel_all_pending_proposals": []}

            if timelock_proposal.id > last_canceled:
                print(f"Canceling proposal {timelock_proposal.id}, total info is {model_proposal}")
                canceled_proposals.append(timelock_proposal.id)

    return {"cancel_all_pending_proposals": canceled_proposals}


def get_proposals_to_schedule_and_execute(params, substep, state_history, prev_state):
    dual_governance: DualGovernance = prev_state["dual_governance"]

    proposals_to_schedule: List[Proposal] = []
    proposals_to_execute: List[Proposal] = []
    for proposal in dual_governance.timelock.proposals.state.proposals:
        if dual_governance.can_schedule(proposal.id) and dual_governance.state.can_schedule_proposal(
            proposal.submittedAt
        ):
            proposals_to_schedule.append(proposal)

        elif dual_governance.can_execute(proposal.id):
            proposals_to_execute.append(proposal)

    return {"proposals_to_schedule": proposals_to_schedule, "proposals_to_execute": proposals_to_execute}


# Mechanisms


def submit_proposals(params, substep, state_history, prev_state, policy_input):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    proposals: List[Proposal] = policy_input["proposal_create"]
    # queue: ProposalQueueManager = prev_state["proposals_queue"]
    timestep: int = prev_state["timestep"]

    if proposals:
        print(f"current timestep is {timestep}")
        print(f"proposals created with monthly queue is {proposals}")

    for proposal in proposals:
        print(
            "submitting proposal with ID",
            proposal.id,
            "at ",
            dual_governance.time_manager.get_current_time(),
            prev_state["timestep"],
        )
        # print(proposal)
        dual_governance.submit_proposal("", [ExecutorCall("", "", [])])

    return ("dual_governance", dual_governance)


def activate_attack(params, substep, state_history, prev_state, policy_input):
    proposals: List[Proposal] = policy_input["proposal_create"]
    scenario: Scenario = prev_state["scenario"]
    current_state = prev_state["is_active_attack"]

    if not proposals:
        return ("is_active_attack", current_state)

    dangerous_types = {
        Scenario.CoordinatedAttack: (ProposalType.Danger, ProposalType.Hack, ProposalType.Negative),
        Scenario.SingleAttack: (ProposalType.Danger, ProposalType.Hack, ProposalType.Negative),
        Scenario.VetoSignallingLoop: (ProposalType.Positive, ProposalType.NoImpact, ProposalType.Random),
        Scenario.ConstantVetoSignallingLoop: (ProposalType.Positive, ProposalType.NoImpact, ProposalType.Random),
    }.get(scenario)

    if not dangerous_types:
        return ("is_active_attack", current_state)

    for proposal in proposals:
        if proposal.proposal_type in dangerous_types:
            return ("is_active_attack", True)

    return ("is_active_attack", current_state)


def deactivate_attack(params, substep, state_history, prev_state, policy_input):
    canceled_proposals = policy_input["cancel_all_pending_proposals"]
    current_state: bool = prev_state["is_active_attack"]

    if not canceled_proposals:
        return ("is_active_attack", current_state)

    scenario: Scenario = prev_state["scenario"]
    dual_governance: DualGovernance = prev_state["dual_governance"]

    dangerous_types = {
        Scenario.CoordinatedAttack: (ProposalType.Danger, ProposalType.Hack, ProposalType.Negative),
        Scenario.SingleAttack: (ProposalType.Danger, ProposalType.Hack, ProposalType.Negative),
        Scenario.VetoSignallingLoop: (ProposalType.Positive, ProposalType.NoImpact, ProposalType.Random),
        Scenario.ConstantVetoSignallingLoop: (ProposalType.Positive, ProposalType.NoImpact, ProposalType.Random),
    }.get(scenario)

    if not dangerous_types:
        return ("is_active_attack", current_state)

    for prop in prev_state["proposals"]:
        if prop.proposal_type in dangerous_types:
            timelock_status = dual_governance.timelock.proposals.get(prop.id).status

            if timelock_status == ProposalStatus.Executed or (prop.id not in canceled_proposals):
                return ("is_active_attack", True)

    return ("is_active_attack", False)


def register_proposals(params, substep, state_history, prev_state, policy_input):
    proposals: List[Proposal] = prev_state["proposals"]
    created_proposals = policy_input["proposal_create"]

    for proposal in created_proposals:
        proposals.append(proposal)

    return ("proposals", proposals)


def initialize_proposals(params, substep, state_history, prev_state, policy_input):
    non_initialized_proposals: List[Proposal] = prev_state["non_initialized_proposals"]
    proposals: List[Proposal] = policy_input["proposal_create"]

    non_initialized_proposals_left = []
    for non_initialized_proposal in non_initialized_proposals:
        initialized = False
        for proposal in proposals:
            if non_initialized_proposal == proposal:
                initialized = True
        if not initialized:
            non_initialized_proposals_left.append(non_initialized_proposal)

    return ("non_initialized_proposals", non_initialized_proposals_left)


def cancel_proposals(params, substep, state_history, prev_state, policy_input):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    proposals_to_cancel = policy_input["cancel_all_pending_proposals"]

    if proposals_to_cancel:
        dual_governance.cancel_all_pending_proposals()

    return ("dual_governance", dual_governance)


def schedule_and_execute_proposals(params, substep, state_history, prev_state, policy_input):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    proposals_to_schedule: List[Proposal] = policy_input["proposals_to_schedule"]
    proposals_to_execute: List[Proposal] = policy_input["proposals_to_execute"]

    for proposal in proposals_to_schedule:
        dual_governance.schedule_proposal(proposal.id)

    for proposal in proposals_to_execute:
        dual_governance.execute_proposal(proposal.id)

    return ("dual_governance", dual_governance)


def _should_cancel_proposal(scenario: Scenario, proposal: Proposal) -> bool:
    """Helper function to determine if a proposal should be canceled based on scenario."""
    if scenario in [Scenario.CoordinatedAttack, Scenario.SingleAttack]:
        return proposal.proposal_type in (
            ProposalType.Danger,
            ProposalType.Hack,
            ProposalType.Negative,
        )
    elif scenario in [Scenario.VetoSignallingLoop, Scenario.ConstantVetoSignallingLoop]:
        return proposal.proposal_type in (
            ProposalType.Positive,
            ProposalType.NoImpact,
            ProposalType.Random,
        )
    elif scenario == Scenario.HappyPath:
        return True
    return False

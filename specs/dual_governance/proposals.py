from dataclasses import dataclass, field
from enum import Enum
from typing import List

from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp


class ProposalErrors:
    class EmptyCalls(Exception):
        pass

    class ProposalCancelled(Exception):
        pass

    class ProposalNotFound(Exception):
        pass

    class ProposalNotScheduled(Exception):
        pass

    class ProposalNotSubmitted(Exception):
        pass

    class AfterSubmitDelayNotPassed(Exception):
        pass

    class AfterScheduleDelayNotPassed(Exception):
        pass


class ExecutorCall:
    target: str
    value: int
    payload: bytes

    def __init__(self, target: str, value: int, payload: bytes):
        self.target = target
        self.value = value
        self.payload = payload


class ProposalStatus(Enum):
    NotExist = 1
    Submitted = 2
    Scheduled = 3
    Executed = 4
    Cancelled = 5


@dataclass
class Proposal:
    id: int = field(default_factory=lambda: 0)
    status: ProposalStatus = field(default_factory=lambda: ProposalStatus.NotExist)
    executor: str = field(default_factory=lambda: "")
    submittedAt: Timestamp = field(default_factory=lambda: Timestamp(0))
    scheduledAt: Timestamp = field(default_factory=lambda: Timestamp(0))
    executedAt: Timestamp = field(default_factory=lambda: Timestamp(0))
    cancelledAt: Timestamp = field(default_factory=lambda: Timestamp(0))
    calls: List[ExecutorCall] = field(default_factory=list)


@dataclass
class ProposalState:
    last_canceled_proposal_id: int = field(default_factory=lambda: 0)
    proposals: List[Proposal] = field(default_factory=list)


@dataclass
class Proposals:
    state: ProposalState = field(default_factory=lambda: ProposalState())
    time_manager: TimeManager = None
    proposal_id_offset: int = 1

    def initialize(self, time_manager: TimeManager):
        self.time_manager = time_manager

    ## ---
    ## main proposal operations
    ## ---

    def submit(self, executor: str, calls: List[ExecutorCall]) -> int:
        if len(calls) == 0:
            raise ProposalErrors.EmptyCalls

        new_proposal_index = len(self.state.proposals)
        new_proposal_id = new_proposal_index + self.proposal_id_offset

        new_proposal = Proposal(
            id=new_proposal_id,
            status=ProposalStatus.Submitted,
            executor=executor,
            submittedAt=Timestamp.from_uint256(self.time_manager.get_current_timestamp()),
            calls=calls,
        )

        self.state.proposals.append(new_proposal)

        return new_proposal_id

    def schedule(self, proposal_id: int, after_submit_delay: int):
        self._check_proposal_submitted(proposal_id)
        if self.is_proposal_marked_cancelled(proposal_id):
            raise ProposalErrors.ProposalNotSubmitted
        self._check_after_submit_delay_passed(proposal_id, after_submit_delay)

        proposal = self._get_proposal(proposal_id)
        proposal.scheduledAt = Timestamp.from_uint256(self.time_manager.get_current_timestamp())
        proposal.status = ProposalStatus.Scheduled

    def execute(self, proposal_id: int, after_schedule_delay: int):
        self._check_proposal_scheduled(proposal_id)
        if self.is_proposal_marked_cancelled(proposal_id):
            raise ProposalErrors.ProposalNotScheduled
        self._check_after_schedule_delay_passed(proposal_id, after_schedule_delay)

        proposal = self._get_proposal(proposal_id)
        proposal.executedAt = Timestamp.from_uint256(self.time_manager.get_current_timestamp())
        proposal.status = ProposalStatus.Executed

    def cancel(self, proposal_id: int):
        proposal = self._get_proposal(proposal_id)
        if proposal.status == ProposalStatus.Executed:
            return
        elif proposal.status == ProposalStatus.Cancelled:
            return
        proposal.cancelledAt = Timestamp.from_uint256(self.time_manager.get_current_timestamp())
        proposal.status = ProposalStatus.Cancelled

    def cancel_all(self):
        for proposal_id in range(self.state.last_canceled_proposal_id + 1):
            if proposal_id == 0:
                continue
            self.cancel(proposal_id)
        last_proposal_id = len(self.state.proposals)
        self.state.last_canceled_proposal_id = last_proposal_id

    ## ---
    ## getter functions
    ## ---

    def get(self, proposal_id: int) -> Proposal:
        self._check_proposal_exist(proposal_id)
        return self._get_proposal(proposal_id)

    def get_proposal_submission_time(self, proposal_id: int) -> Timestamp:
        self._check_proposal_exist(proposal_id)
        proposal = self._get_proposal(proposal_id)
        return proposal.submittedAt

    def count(self) -> int:
        return len(self.state.proposals)

    ## ---
    ## external checks
    ## ---

    def can_execute(self, proposal_id: int, after_schedule_delay: int) -> bool:
        proposal = self._get_proposal(proposal_id)
        if self.is_proposal_marked_cancelled(proposal_id):
            return False

        return (proposal.status == ProposalStatus.Scheduled) and (
            Timestamp.from_uint256(self.time_manager.get_current_timestamp())
            >= proposal.scheduledAt + Timestamp.from_uint256(after_schedule_delay)
        )

    def can_schedule(self, proposal_id: int, after_submit_delay: int) -> bool:
        proposal = self._get_proposal(proposal_id)
        if self.is_proposal_marked_cancelled(proposal_id):
            return False

        return (proposal.status == ProposalStatus.Submitted) and (
            Timestamp.from_uint256(self.time_manager.get_current_timestamp())
            >= proposal.submittedAt + Timestamp.from_uint256(after_submit_delay)
        )

    ## ---
    ## internal functions
    ## ---

    def _check_proposal_exist(self, proposal_id: int):
        if proposal_id < self.proposal_id_offset or proposal_id > len(self.state.proposals):
            raise ProposalErrors.ProposalNotFound

    def _check_proposal_submitted(self, proposal_id: int):
        proposal = self._get_proposal(proposal_id)
        if proposal.status != ProposalStatus.Submitted:
            raise ProposalErrors.ProposalNotSubmitted

    def _check_proposal_scheduled(self, proposal_id: int):
        proposal = self._get_proposal(proposal_id)
        if proposal.status != ProposalStatus.Scheduled:
            raise ProposalErrors.ProposalNotScheduled

    def _check_after_submit_delay_passed(self, proposal_id: int, after_submit_delay: int):
        proposal = self._get_proposal(proposal_id)
        if Timestamp.from_uint256(
            self.time_manager.get_current_timestamp()
        ) < proposal.submittedAt + Timestamp.from_uint256(after_submit_delay):
            raise ProposalErrors.AfterSubmitDelayNotPassed

    def _check_after_schedule_delay_passed(self, proposal_id: int, after_schedule_delay: int):
        proposal = self._get_proposal(proposal_id)
        if Timestamp.from_uint256(
            self.time_manager.get_current_timestamp()
        ) < proposal.scheduledAt + Timestamp.from_uint256(after_schedule_delay):
            raise ProposalErrors.AfterScheduleDelayNotPassed

    def _get_proposal(self, proposal_id: int) -> Proposal:
        return self.state.proposals[proposal_id - self.proposal_id_offset]

    def is_proposal_marked_cancelled(self, proposal_id: int) -> bool:
        proposal = self._get_proposal(proposal_id)

        return proposal_id <= self.state.last_canceled_proposal_id and proposal.status != ProposalStatus.Executed

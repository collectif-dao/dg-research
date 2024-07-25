from dataclasses import dataclass
from datetime import timedelta
from typing import List

from specs.dual_governance.proposals import ExecutorCall, Proposal, Proposals, ProposalStatus
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp
from specs.utils import default


@dataclass
class EmergencyProtectedTimelock:
    proposals: Proposals = None
    time_manager: TimeManager = None

    after_submit_delay: int = default(int(timedelta(days=3).total_seconds()))
    after_schedule_delay: int = default(int(timedelta(days=2).total_seconds()))

    def initialize(self, time_manager: TimeManager):
        self.time_manager = time_manager
        self.proposals = Proposals()
        self.proposals.initialize(time_manager)

    ## ---
    ## proposals operations
    ## ---

    def submit(self, executor: str, calls: List[ExecutorCall]) -> int:
        return self.proposals.submit(executor, calls)

    def schedule(self, proposal_id: int):
        self.proposals.schedule(proposal_id, self.after_submit_delay)

    def execute(self, proposal_id: int):
        self.proposals.execute(proposal_id, self.after_schedule_delay)

    def cancel_all_non_executed_proposals(self):
        self.proposals.cancel_all()

    ## ---
    ## proposals get functions
    ## ---

    def get_proposal(self, proposal_id: int) -> Proposal:
        return self.proposals.get(proposal_id)

    def get_proposal_status(self, proposal_id: int) -> ProposalStatus:
        return self.proposals.get(proposal_id).status

    def get_proposal_count(self) -> int:
        return self.proposals.count()

    def get_proposal_submission_time(self, proposal_id: int) -> Timestamp:
        return self.proposals.get_proposal_submission_time(proposal_id)

    def can_schedule(self, proposal_id: int) -> bool:
        return self.proposals.can_schedule(proposal_id, self.after_submit_delay)

    def can_execute(self, proposal_id: int) -> bool:
        return self.proposals.can_execute(proposal_id, self.after_schedule_delay)

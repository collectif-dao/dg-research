from dataclasses import dataclass
from datetime import timedelta
from typing import List

from specs.dual_governance.emergency_protection import EmergencyProtection, EmergencyState
from specs.dual_governance.proposals import ExecutorCall, Proposal, Proposals, ProposalStatus
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp
from specs.utils import default


@dataclass
class EmergencyProtectedTimelock:
    proposals: Proposals = None
    time_manager: TimeManager = None
    emergency_protection: EmergencyProtection = None

    after_submit_delay: int = default(int(timedelta(days=3).total_seconds()))
    after_schedule_delay: int = default(int(timedelta(days=2).total_seconds()))

    def initialize(self, time_manager: TimeManager, after_schedule_delay: int = 0):
        self.time_manager = time_manager
        self.proposals = Proposals()
        self.proposals.initialize(time_manager)
        if after_schedule_delay > 0:
            self.after_schedule_delay = int(timedelta(days=after_schedule_delay).total_seconds())

    ## ---
    ## proposals operations
    ## ---

    def submit(self, executor: str, calls: List[ExecutorCall]) -> int:
        return self.proposals.submit(executor, calls)

    def schedule(self, proposal_id: int):
        self.proposals.schedule(proposal_id, self.after_submit_delay)

    def execute(self, proposal_id: int):
        self.emergency_protection.check_emergency_mode_status(False)
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
        return self.emergency_protection.is_emergency_mode_activated() is not True and self.proposals.can_execute(
            proposal_id, self.after_schedule_delay
        )

    ## ---
    ## emergency protection
    ## ---

    def set_emergency_protection(
        self,
        activation_committee: str,
        execution_committee: str,
        protection_duration: Timestamp,
        emergency_mode_duration: Timestamp,
    ):
        emergency_protection = EmergencyProtection()
        emergency_protection.setup(
            activation_committee, execution_committee, protection_duration, emergency_mode_duration, self.time_manager
        )
        self.emergency_protection = emergency_protection

    def activate_emergency_mode(self, activation_committee: str):
        self.emergency_protection.check_activation_committee(activation_committee)
        self.emergency_protection.check_emergency_mode_status(False)
        self.emergency_protection.activate()

    def deactivate_emergency_mode(self):
        self.emergency_protection.check_emergency_mode_status(True)
        self.emergency_protection.deactivate()
        self.proposals.cancel_all()

    def emergency_execute(self, executor: str, proposal_id: int):
        self.emergency_protection.check_emergency_mode_status(True)
        self.emergency_protection.check_execution_committee(executor)
        self.proposals.execute(proposal_id, 0)

    def emergency_reset(self, executor):
        self.emergency_protection.check_emergency_mode_status(True)
        self.emergency_protection.check_execution_committee(executor)
        self.emergency_protection.deactivate()
        self.proposals.cancel_all()

    def is_emergency_protection_enabled(self) -> bool:
        return self.emergency_protection.is_emergency_protection_enabled()

    def get_emergency_state(self) -> EmergencyState:
        return self.emergency_protection.get_emergency_state()

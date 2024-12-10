from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from specs.committees.tiebreaker_core import TiebreakerCore
from specs.dual_governance.config import DualGovernanceConfig
from specs.dual_governance.proposals import ExecutorCall
from specs.dual_governance.state import DualGovernanceState, State
from specs.dual_governance.timelock import EmergencyProtectedTimelock
from specs.escrow.escrow import Escrow
from specs.lido import Lido
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp


@dataclass
class DualGovernance:
    state: DualGovernanceState = None
    timelock: EmergencyProtectedTimelock = None
    time_manager: TimeManager = None
    tiebreaker: TiebreakerCore = None
    reseal_manager: str = None

    def initialize(
        self,
        escrow_address: str,
        time_manager: TimeManager,
        lido: Lido,
        activation_committee: str = "",
        execution_committee: str = "",
        protection_duration: Timestamp = Timestamp(0),
        emergency_mode_duration: Timestamp = Timestamp(0),
        after_schedule_delay: int = 0,
        **config_overrides,
    ):
        self.time_manager = time_manager
        timelock = EmergencyProtectedTimelock()
        timelock.initialize(time_manager, after_schedule_delay)
        timelock.set_emergency_protection(
            activation_committee,
            execution_committee,
            protection_duration,
            emergency_mode_duration,
        )

        self.timelock = timelock

        config = DualGovernanceConfig(**config_overrides)
        dgState = DualGovernanceState(config)
        dgState.initialize(escrow_address, time_manager, lido=lido)
        self.state = dgState

    ## ---
    ## proposals section
    ## ---

    def submit_proposal(self, executor: str, calls: List[ExecutorCall]) -> int:
        self.state.activate_next_state()
        self.state.check_proposals_creation_allowed()

        return self.timelock.submit(executor, calls)

    def schedule_proposal(self, proposal_id: int):
        self.state.activate_next_state()

        proposal_submission_time = self.timelock.get_proposal_submission_time(proposal_id)
        self.state.check_can_schedule_proposal(proposal_submission_time)

        self.timelock.schedule(proposal_id)

    def execute_proposal(self, proposal_id: int):
        if self.can_execute(proposal_id):
            self.timelock.execute(proposal_id)

    def cancel_all_pending_proposals(self):
        self.timelock.cancel_all_non_executed_proposals()

    def get_veto_signalling_escrow(self) -> Escrow:
        return self.state.signalling_escrow

    def get_rage_quit_escrow(self) -> Escrow:
        return self.state.rage_quit_escrow

    def can_schedule(self, proposal_id: int) -> bool:
        return self.state.is_proposals_adoption_allowed() and self.timelock.can_schedule(proposal_id)

    def can_execute(self, proposal_id: int) -> bool:
        return self.state.is_proposals_adoption_allowed() and self.timelock.can_execute(proposal_id)

    ## ---
    ## state transitions section
    ## ---

    def activate_next_state(self):
        self.state.activate_next_state()

    def get_current_state(self) -> State:
        return self.state.current_state()

    def get_veto_signalling_state(self) -> tuple[bool, int, Timestamp, Timestamp]:
        return self.state.get_veto_signalling_state()

    def get_veto_signalling_deactivation_state(self) -> tuple[bool, timedelta, datetime]:
        return self.state.get_veto_signalling_deactivation_state()

    def get_veto_signalling_duration(self) -> timedelta:
        return self.state.get_veto_signalling_duration()

    def is_scheduling_enabled(self) -> bool:
        return self.state.is_proposals_adoption_allowed()

    def is_creation_enabled(self) -> bool:
        return self.state.is_proposals_creation_allowed()

    ## ---
    ## tiebreaker section
    ## ---

    def tiebreaker_resume_sealable(self, tiebreaker: str, sealable: str):
        self.check_tiebreaker_committee(tiebreaker)
        self.state.check_tiebreak()
        self.reseal_manager.resume(sealable)

    def tiebreaker_schedule_proposal(self, tiebreaker: str, proposal_id: int):
        self.check_tiebreaker_committee(tiebreaker)
        self.state.check_tiebreak()
        self.timelock.schedule(proposal_id)

    def set_tiebreaker_protection(self, tiebreaker: TiebreakerCore, reseal_manager):
        self.tiebreaker = tiebreaker
        self.reseal_manager = reseal_manager

    def check_tiebreaker_committee(self, tiebreaker: str):
        if tiebreaker != self.tiebreaker.address:
            raise Exception("NotTiebreaker")

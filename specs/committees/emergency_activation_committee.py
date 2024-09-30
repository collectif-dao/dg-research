from dataclasses import dataclass
from typing import List

from specs.committees.hash_consensus import Errors, HashConsensus
from specs.dual_governance.timelock import EmergencyProtectedTimelock
from specs.time_manager import TimeManager


@dataclass
class EmergencyActivationCommittee(HashConsensus):
    timelock: EmergencyProtectedTimelock = None
    time_manager: TimeManager = None
    hash: str = "EMERGENCY_ACTIVATE"
    address: str = ""

    def initialize(
        self,
        new_members: List[str],
        execution_quorum: int,
        timelock_duration: int,
        time_manager: TimeManager,
        timelock: EmergencyProtectedTimelock,
        address: str = "",
    ):
        super().initialize(new_members, execution_quorum, timelock_duration, time_manager)

        self.timelock = timelock
        self.time_manager = time_manager
        self.address = address

    def approve_emergency_activate(self, voter: str):
        if voter not in self.members:
            raise Errors.IsNotMember

        self.vote(voter, self.hash, True)

    def get_emergency_activate_state(self) -> tuple[int, int, bool]:
        return self.get_hash_state(self.hash)

    def execute_emergency_activate(self):
        self.mark_used(self.hash)
        self.timelock.activate_emergency_mode(self.address)

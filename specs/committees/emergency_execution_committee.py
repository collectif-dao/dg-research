from dataclasses import dataclass
from typing import List, Tuple

from eth_abi import encode
from eth_utils import keccak

from specs.committees.hash_consensus import Errors, HashConsensus
from specs.committees.proposals_list import ProposalsList
from specs.dual_governance.timelock import EmergencyProtectedTimelock
from specs.time_manager import TimeManager


class ProposalType:
    EmergencyExecute = 1
    EmergencyReset = 2


@dataclass
class EmergencyExecutionCommittee(HashConsensus, ProposalsList):
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
        super().setup(time_manager)

        self.timelock = timelock
        self.time_manager = time_manager
        self.address = address

    ## ---
    ## emergency execution
    ## ---

    def vote_emergency_execute(self, proposal_id: int, voter: str, supports: bool):
        if voter not in self.members:
            raise Errors.IsNotMember

        proposal_data, key = self._encode_emergency_execute(proposal_id)

        self.vote(voter, key, supports)
        self._push_proposal(key, int(ProposalType.EmergencyExecute), proposal_data)

    def execute_emergency_execute(self, proposal_id: int):
        _, key = self._encode_emergency_execute(proposal_id)
        self.mark_used(key)

        self.timelock.emergency_execute(self.address, proposal_id)

    ## ---
    ## emergency reset
    ## ---

    def approve_emergency_reset(self, voter: str):
        if voter not in self.members:
            raise Errors.IsNotMember

        proposal_key = self._encode_emergency_reset_proposal_key()
        self.vote(voter, proposal_key, True)
        self._push_proposal(proposal_key, int(ProposalType.EmergencyReset), b"")

    def execute_emergency_reset(self):
        proposal_key = self._encode_emergency_reset_proposal_key()

        self.mark_used(proposal_key)
        self.timelock.emergency_reset(self.address)

    ## ---
    ## get functions
    ## ---

    def get_emergency_execute_state(self, proposal_id: int) -> Tuple[int, int, bool]:
        _, key = self._encode_emergency_execute(proposal_id)
        return self.get_hash_state(key)

    def get_emergency_reset_state(self) -> Tuple[int, int, bool]:
        proposal_key = self._encode_emergency_reset_proposal_key()
        return self.get_hash_state(proposal_key)

    ## ---
    ## internal methods
    ## ---

    def _encode_emergency_execute(self, proposal_id: int) -> Tuple[bytes, bytes]:
        proposal_data = encode(["uint8", "uint256"], [ProposalType.EmergencyExecute, proposal_id])
        key = keccak(proposal_data)

        return proposal_data, key

    def _encode_emergency_reset_proposal_key(self) -> bytes:
        return keccak(encode(["uint8", "bytes"], [ProposalType.EmergencyReset, b""]))

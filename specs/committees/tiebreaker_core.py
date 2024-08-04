from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from eth_abi import encode
from eth_utils import keccak

from specs.committees.hash_consensus import Errors, HashConsensus
from specs.committees.proposals_list import ProposalsList
from specs.time_manager import TimeManager


class ProposalType:
    ScheduleProposal = 1
    ResumeSealable = 2


@dataclass
class TiebreakerCore(HashConsensus, ProposalsList):
    dual_governance: Any = None
    time_manager: TimeManager = None
    address: str = ""
    sealable_resume_nonces: Dict[str, int] = field(default_factory=dict)

    def initialize(
        self,
        new_members: List[str],
        execution_quorum: int,
        timelock_duration: int,
        time_manager: TimeManager,
        dual_governance: Any,
        address: str = "",
    ):
        super().initialize(new_members, execution_quorum, timelock_duration, time_manager)
        super().setup(time_manager)

        self.dual_governance = dual_governance
        self.time_manager = time_manager
        self.address = address

    ## ---
    ## tiebreaker schedule proposal
    ## ---

    def schedule_proposal(self, proposal_id: int, voter: str):
        if voter not in self.members:
            raise Errors.IsNotMember

        proposal_data, key = self.encode_schedule_proposal(proposal_id)

        self.vote(voter, key, True)
        self._push_proposal(key, int(ProposalType.ScheduleProposal), proposal_data)

    def execute_schedule_proposal(self, proposal_id: int):
        _, key = self.encode_schedule_proposal(proposal_id)
        self.mark_used(key)

        self.dual_governance.tiebreaker_schedule_proposal(self.address, proposal_id)

    ## ---
    ## tiebreaker sealable resume
    ## ---

    def sealable_resume(self, sealable: str, nonce: int, voter: str):
        if nonce != self.sealable_resume_nonces[sealable]:
            raise Exception("ResumeSealableNonceMismatch")

        proposal_data, key = self.encode_sealable_resume(sealable, nonce)

        self.vote(voter, key, True)
        self._push_proposal(key, int(ProposalType.ResumeSealable), proposal_data)

    def execute_sealable_resume(self, sealable: str):
        _, key = self.encode_sealable_resume(sealable, self.sealable_resume_nonces[sealable])
        self.mark_used(key)
        self.sealable_resume_nonces[sealable] += 1

        self.dual_governance.tiebreaker_resume_sealable(self.address, sealable)

    ## ---
    ## getter methods
    ## ---

    def get_schedule_proposal_state(self, proposal_id: int) -> Tuple[int, int, bool]:
        _, key = self.encode_schedule_proposal(proposal_id)
        return self.get_hash_state(key)

    def get_sealable_resume_state(self, sealable: str, nonce: int) -> Tuple[int, int, bool]:
        _, key = self.encode_sealable_resume(sealable, nonce)
        return self.get_hash_state(key)

    def get_sealable_resume_nonce(self, sealable: str) -> int:
        return self.sealable_resume_nonces[sealable]

    ## ---
    ## encoding functions
    ## ---

    def encode_schedule_proposal(self, proposal_id: int) -> Tuple[bytes, bytes]:
        proposal_data = encode(["uint8", "uint256"], [ProposalType.ScheduleProposal, proposal_id])
        key = keccak(proposal_data)

        return proposal_data, key

    def encode_sealable_resume(self, sealable: str, nonce: int) -> Tuple[bytes, bytes]:
        proposal_data = encode(["uint8", "address", "uint256"], [ProposalType.ScheduleProposal, sealable, nonce])
        key = keccak(proposal_data)

        return proposal_data, key

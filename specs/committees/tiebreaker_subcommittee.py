from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from eth_abi import encode
from eth_utils import keccak

from specs.committees.hash_consensus import Errors, HashConsensus
from specs.committees.proposals_list import ProposalsList
from specs.committees.tiebreaker_core import ProposalType, TiebreakerCore
from specs.time_manager import TimeManager


# noinspection PyMethodMayBeStatic
@dataclass
class TiebreakerSubCommittee(HashConsensus, ProposalsList):
    tiebreaker_core: TiebreakerCore = None
    time_manager: TimeManager = None
    address: str = ""
    sealable_resume_nonces: Dict[str, int] = field(default_factory=dict)

    def initialize(
        self,
        new_members: List[str],
        execution_quorum: int,
        timelock_duration: int,
        time_manager: TimeManager,
        tiebreaker_core: TiebreakerCore,
        address: str = "",
    ):
        super().initialize(new_members, execution_quorum, timelock_duration, time_manager)
        super().setup(time_manager)

        self.tiebreaker_core = tiebreaker_core
        self.time_manager = time_manager
        self.address = address

    ## ---
    ## tiebreaker subcommittee schedule proposal
    ## ---

    def schedule_proposal(self, proposal_id: int, voter: str):
        if voter not in self.members:
            raise Errors.IsNotMember

        proposal_data, key = self.encode_approve_schedule_proposal(proposal_id)

        self.vote(voter, key, True)
        self._push_proposal(key, int(ProposalType.ScheduleProposal), proposal_data)

    def execute_schedule_proposal(self, proposal_id: int):
        _, key = self.encode_approve_schedule_proposal(proposal_id)
        self.mark_used(key)

        self.tiebreaker_core.schedule_proposal(proposal_id, self.address)

    def encode_approve_schedule_proposal(self, proposal_id: int) -> Tuple[bytes, bytes]:
        proposal_data = encode(["uint8", "uint256"], [ProposalType.ScheduleProposal, proposal_id])
        key = keccak(proposal_data)

        return proposal_data, key

    def get_schedule_proposal_state(self, proposal_id: int) -> Tuple[int, int, bool]:
        _, key = self.encode_approve_schedule_proposal(proposal_id)
        return self.get_hash_state(key)

    ## ---
    ## tiebreaker subcommittee sealable resume
    ## ---

    def sealable_resume(self, sealable: str, voter: str):
        proposal_data, key, _ = self.encode_sealable_resume(sealable)

        self.vote(voter, key, True)
        self._push_proposal(key, int(ProposalType.ResumeSealable), proposal_data)

    def execute_sealable_resume(self, sealable: str):
        _, key, nonce = self.encode_sealable_resume(sealable)
        self.mark_used(key)

        self.tiebreaker_core.sealable_resume(sealable, nonce, self.address)

        self.dual_governance.tiebreaker_resume_sealable(self.address, sealable)

    def get_sealable_resume_state(self, sealable: str) -> Tuple[int, int, bool]:
        _, key, _ = self.encode_sealable_resume(sealable)
        return self.get_hash_state(key)

    def encode_sealable_resume(self, sealable: str) -> Tuple[bytes, bytes, int]:
        nonce = self.tiebreaker_core.get_sealable_resume_nonce(sealable)

        proposal_data = encode(["address", "uint256"], [sealable, nonce])
        key = keccak(proposal_data)

        return proposal_data, key, nonce

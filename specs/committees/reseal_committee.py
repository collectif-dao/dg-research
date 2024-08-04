from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from eth_abi import encode
from eth_utils import keccak

from specs.committees.hash_consensus import Errors, HashConsensus
from specs.committees.proposals_list import ProposalsList
from specs.time_manager import TimeManager


@dataclass
class ResealCommittee(HashConsensus, ProposalsList):
    dual_governance: Any = None
    time_manager: TimeManager = None
    address: str = ""
    reseal_nonces: Dict[bytes, int] = field(default_factory=dict)

    def initialize(
        self,
        new_members: List[str],
        execution_quorum: int,
        timelock_duration: int,
        time_manager: TimeManager,
        dual_governance: Any = {},
        address: str = "",
    ):
        super().initialize(new_members, execution_quorum, timelock_duration, time_manager)
        super().setup(time_manager)

        self.dual_governance = dual_governance
        self.time_manager = time_manager
        self.address = address

    def vote_reseal(self, voter: str, sealables: list[str], support: bool):
        if voter not in self.members:
            raise Errors.IsNotMember

        proposal_data, key = self.encode_reseal_proposal(sealables)
        print("key during vote_reseal: ", key)

        self.vote(voter, key, support)
        self._push_proposal(key, 0, proposal_data)

    def execute_reseal(self, sealables: list[str]):
        _, key = self.encode_reseal_proposal(sealables)
        self.mark_used(key)

        # self.dual_governance.reseal(self.address, sealables) // TODO: implement the call

        reseal_nonce_hash = keccak(encode(["address[]"], [sealables]))
        self.reseal_nonces[reseal_nonce_hash] += 1

    def get_reseal_state(self, sealables: list[str]) -> Tuple[int, int, bool]:
        _, key = self.encode_reseal_proposal(sealables)
        print("key in get_reseal_state: ", key)

        return self.get_hash_state(key)

    def encode_reseal_proposal(self, sealables: list[str]) -> Tuple[bytes, bytes]:
        reseal_nonce_hash = keccak(encode(["address[]"], [sealables]))

        if reseal_nonce_hash not in self.reseal_nonces:
            self.reseal_nonces[reseal_nonce_hash] = 0

        nonce = self.reseal_nonces[reseal_nonce_hash]

        proposal_data = encode(["address[]", "uint256"], [sealables, nonce])
        key = keccak(proposal_data)

        return proposal_data, key

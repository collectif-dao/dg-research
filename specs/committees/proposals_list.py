from dataclasses import dataclass, field
from typing import List, Optional

from specs.committees.enumerable_proposals import Bytes32ToProposalMap, Proposal
from specs.time_manager import TimeManager


@dataclass
class ProposalsList:
    proposals: Bytes32ToProposalMap = field(default_factory=Bytes32ToProposalMap)

    def setup(self, time_manager: TimeManager):
        self.proposals.setup(time_manager)

    def get_proposals(self, offset: int, limit: int) -> List[Proposal]:
        keys = self.proposals.get_ordered_keys_subset(offset, limit)

        return [self.proposals.get(key) for key in keys]

    def get_proposal_at(self, index: int) -> Optional[Proposal]:
        return self.proposals.at(index)

    def get_proposal(self, key: bytes) -> Optional[Proposal]:
        return self.proposals.get(key)

    def get_proposals_length(self) -> int:
        return self.proposals.length()

    def get_ordered_keys(self, offset: int, limit: int) -> List[bytes]:
        return self.proposals.get_ordered_keys_subset(offset, limit)

    def _push_proposal(self, key: bytes, proposal_type: int, data: bytes) -> None:
        self.proposals.push(key, proposal_type, data)

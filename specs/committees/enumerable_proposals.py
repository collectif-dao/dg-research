from dataclasses import dataclass, field
from typing import Dict, List, Optional

from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp


@dataclass
class Proposal:
    submitted_at: Timestamp
    proposal_type: int
    data: bytes


@dataclass
class Bytes32ToProposalMap:
    ordered_keys: List[bytes] = field(default_factory=list)
    keys: Dict[bytes, bool] = field(default_factory=dict)
    proposals: Dict[bytes, Proposal] = field(default_factory=dict)
    time_manager: TimeManager = None

    def setup(
        self,
        time_manager: TimeManager,
    ):
        self.time_manager = time_manager

    def push(self, key: bytes, proposal_type: int, data: bytes) -> bool:
        if not self.contains(key):
            proposal = Proposal(self.time_manager.get_current_timestamp_value(), proposal_type, data)
            self.proposals[key] = proposal
            self.ordered_keys.append(key)
            self.keys[key] = True
            return True

        return False

    def contains(self, key: bytes) -> bool:
        return key in self.keys

    def length(self) -> int:
        return len(self.ordered_keys)

    def at(self, index: int) -> Optional[Proposal]:
        if index < 0 or index >= len(self.ordered_keys):
            return None

        key = self.ordered_keys[index]

        return self.proposals.get(key, None)

    def get(self, key: bytes) -> Optional[Proposal]:
        if not self.contains(key):
            raise Exception("ProposalDoesNotExist")

        return self.proposals.get(key, None)

    def get_ordered_keys(self) -> List[bytes]:
        return self.ordered_keys

    def get_ordered_keys_subset(self, offset: int, limit: int) -> List[bytes]:
        if offset >= len(self.ordered_keys):
            raise Exception("OffsetOutOfBounds")

        end = offset + limit
        if end > len(self.ordered_keys):
            end = len(self.ordered_keys)

        return self.ordered_keys[offset:end]

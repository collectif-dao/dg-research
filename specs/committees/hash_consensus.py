from dataclasses import dataclass, field
from typing import Dict, List

from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp, Timestamps


class Errors:
    class Error(Exception):
        pass

    class IsNotMember(Error):
        pass

    class SenderIsNotMember(Error):
        pass

    class HashAlreadyUsed(Error):
        pass

    class QuorumIsNotReached(Error):
        pass

    class InvalidQuorum(Error):
        pass

    class DuplicatedMember(Error):
        pass

    class TimelockNotPassed(Error):
        pass


@dataclass
class HashState:
    quorum_at: Timestamp = field(default_factory=lambda: Timestamps.ZERO)
    used_at: Timestamp = field(default_factory=lambda: Timestamps.ZERO)


@dataclass
class HashConsensus:
    owner: str = ""
    members: Dict[str, bool] = field(default_factory=dict)
    quorum: int = field(default_factory=lambda: 0)
    timelock_duration: Timestamp = field(default_factory=lambda: Timestamps.ZERO)
    hash_states: Dict[str, HashState] = field(default_factory=dict)
    approves: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    time_manager: TimeManager = None

    def initialize(self, new_members: List[str], execution_quorum: int, timelock: int, time_manager: TimeManager):
        if execution_quorum == 0:
            raise Errors.InvalidQuorum

        self.quorum = execution_quorum
        self.timelock_duration = Timestamp(timelock)

        for member in new_members:
            self._add_member(member)

        self.time_manager = time_manager

    def vote(self, signer: str, hash: str, support: bool):
        if hash not in self.hash_states:
            self.hash_states[hash] = HashState()

        if self.hash_states[hash].used_at > Timestamps.ZERO:
            raise Errors.HashAlreadyUsed

        if self.approves.get(signer, {}).get(hash) == support:
            return

        heads = self._get_support(hash)

        if heads == self.quorum - 1 and support:
            self.hash_states[hash].quorum_at = self.time_manager.get_current_timestamp_value()

        self.approves.setdefault(signer, {})[hash] = support

    def mark_used(self, hash: str):
        if self.hash_states[hash].used_at > Timestamps.ZERO:
            raise Errors.HashAlreadyUsed

        if self._get_support(hash) < self.quorum:
            raise Errors.QuorumIsNotReached

        if self.time_manager.get_current_timestamp_value() < self.hash_states[hash].quorum_at + self.timelock_duration:
            raise Errors.TimelockNotPassed

        self.hash_states[hash].used_at = self.time_manager.get_current_timestamp_value()

    def get_hash_state(self, hash: str):
        support = self._get_support(hash)
        execution_quorum = self.quorum
        is_used = self.hash_states[hash].used_at > Timestamps.ZERO

        return support, execution_quorum, is_used

    def add_member(self, new_member: str, new_quorum: int):
        self._add_member(new_member)

        if new_quorum == 0 or new_quorum > len(self.members):
            raise Errors.InvalidQuorum

        self.quorum = new_quorum

    def remove_member(self, member_to_remove: str, new_quorum: int):
        if not self.members.get(member_to_remove, False):
            raise Errors.IsNotMember

        del self.members[member_to_remove]

        if new_quorum == 0 or new_quorum > len(self.members):
            raise Errors.InvalidQuorum

        self.quorum = new_quorum

    def get_members(self) -> List[str]:
        return list(self.members.keys())

    def is_member(self, member: str) -> bool:
        return self.members.get(member, False)

    def set_timelock_duration(self, timelock: int):
        self.timelock_duration = Timestamp(timelock)

    def set_quorum(self, new_quorum: int):
        if new_quorum == 0 or new_quorum > len(self.members):
            raise Errors.InvalidQuorum

        self.quorum = new_quorum

    def _add_member(self, new_member: str):
        if self.members.get(new_member, False):
            raise Errors.DuplicatedMember

        self.members[new_member] = True

    def _get_support(self, hash: str) -> int:
        support = 0

        for member in self.members:
            if self.approves.get(member, {}).get(hash, False):
                support += 1

        return support

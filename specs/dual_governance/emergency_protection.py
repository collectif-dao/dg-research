from dataclasses import dataclass, field

from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp, Timestamps


@dataclass
class EmergencyState:
    execution_committee: str = field(default_factory=lambda: "")
    activation_committee: str = field(default_factory=lambda: "")
    protected_till: Timestamp = field(default_factory=lambda: Timestamps.ZERO)
    is_emergency_mode_activated: bool = False
    emergency_mode_duration: Timestamp = field(default_factory=lambda: Timestamps.ZERO)
    emergency_mode_ends_after: Timestamp = field(default_factory=lambda: Timestamps.ZERO)


@dataclass
class EmergencyProtection:
    activation_committee: str = field(default_factory=lambda: "")
    protected_till: Timestamp = field(default_factory=lambda: Timestamps.ZERO)
    emergency_mode_ends_after: Timestamp = field(default_factory=lambda: Timestamps.ZERO)
    emergency_mode_duration: Timestamp = field(default_factory=lambda: Timestamps.ZERO)
    execution_committee: str = field(default_factory=lambda: "")
    time_manager: TimeManager = None

    def setup(
        self,
        activation_committee: str,
        execution_committee: str,
        protection_duration: Timestamp,
        emergency_mode_duration: Timestamp,
        time_manager: TimeManager,
    ):
        if activation_committee != self.activation_committee:
            self.activation_committee = activation_committee

        if execution_committee != self.execution_committee:
            self.execution_committee = execution_committee

        new_protected_till = time_manager.get_current_timestamp_value() + protection_duration
        if new_protected_till != self.protected_till:
            self.protected_till = new_protected_till

        if emergency_mode_duration != self.emergency_mode_duration:
            self.emergency_mode_duration = emergency_mode_duration

        self.time_manager = time_manager

    def activate(self):
        now = self.time_manager.get_current_timestamp_value()
        if now > self.protected_till:
            raise Exception("EmergencyCommitteeExpired")

        self.emergency_mode_ends_after = self.emergency_mode_duration + now

    def deactivate(self):
        self.activation_committee = None
        self.execution_committee = None
        self.protected_till = Timestamps.ZERO
        self.emergency_mode_ends_after = Timestamps.ZERO
        self.emergency_mode_duration = Timestamps.ZERO

    def get_emergency_state(self) -> EmergencyState:
        return EmergencyState(
            execution_committee=self.execution_committee,
            activation_committee=self.activation_committee,
            protected_till=self.protected_till,
            emergency_mode_duration=self.emergency_mode_duration,
            emergency_mode_ends_after=self.emergency_mode_ends_after,
            is_emergency_mode_activated=self.is_emergency_mode_activated(),
        )

    def is_emergency_mode_activated(self) -> bool:
        return self.emergency_mode_ends_after.is_not_zero()

    def is_emergency_mode_passed(self) -> bool:
        ends_after = self.emergency_mode_ends_after
        return ends_after.is_not_zero() and self.time_manager.get_current_timestamp_value() > ends_after

    def is_emergency_protection_enabled(self) -> bool:
        return (
            self.time_manager.get_current_timestamp_value() <= self.protected_till
            or self.emergency_mode_ends_after.is_not_zero()
        )

    def check_activation_committee(self, account: str):
        if self.activation_committee != account:
            raise Exception("NotEmergencyActivator")

    def check_execution_committee(self, account: str):
        if self.execution_committee != account:
            raise Exception("NotEmergencyEnactor")

    def check_emergency_mode_status(self, expected: bool):
        actual = self.is_emergency_mode_activated()
        if actual != expected:
            raise Exception("InvalidEmergencyModeStatus")

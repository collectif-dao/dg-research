from dataclasses import dataclass, field

from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp, Timestamps


@dataclass
class Pausable:
    resume_since_timestamp: Timestamp = field(default_factory=lambda: Timestamps.ZERO)
    pause_infinite: Timestamp = Timestamps.MAX

    time_manager: TimeManager = None

    def initialize(self, time_manager: TimeManager):
        self.time_manager = time_manager

    def _check_paused(self):
        if not self.is_paused():
            raise Exception("PausedExpected")

    def _check_resumed(self):
        if self.is_paused():
            raise Exception("ResumedExpected")

    def is_paused(self) -> bool:
        return self.time_manager.get_current_timestamp_value() < self.resume_since_timestamp

    def get_resume_since_timestamp(self) -> Timestamp:
        return self.resume_since_timestamp

    def _resume(self):
        self._check_paused()
        self.resume_since_timestamp = self.time_manager.get_current_timestamp_value()

    def _pause_for(self, duration: Timestamp):
        self._check_resumed()
        if duration == Timestamps.ZERO:
            raise Exception("ZeroPauseDuration")

        resume_since = (
            self.pause_infinite
            if duration == self.pause_infinite
            else self.time_manager.get_current_timestamp_value() + duration
        )

        self.resume_since_timestamp = resume_since

    def _pause_until(self, pause_until_inclusive: Timestamp):
        self._check_resumed()
        if pause_until_inclusive < self.time_manager.get_current_timestamp_value():
            raise Exception("PauseUntilMustBeInFuture")

        resume_since = (
            self.pause_infinite
            if pause_until_inclusive == self.pause_infinite
            else pause_until_inclusive + Timestamp(1)
        )

        self.resume_since_timestamp = resume_since

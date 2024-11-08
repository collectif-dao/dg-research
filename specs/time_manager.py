from dataclasses import dataclass, field
from datetime import datetime, timedelta

from specs.types.timestamp import Timestamp


@dataclass
class TimeManager:
    current_time: datetime = field(default_factory=lambda: datetime.min)
    simulation_start_time: datetime = field(default_factory=lambda: datetime.min)

    def initialize(self):
        self.current_time = datetime.now()
        self.simulation_start_time = self.current_time

    def shift_current_time(self, delta: timedelta):
        self.current_time = self.current_time + delta

    def shift_current_timestamp(self, delta: Timestamp):
        current_timestamp = self.get_current_timestamp_value()
        self.current_time = datetime.fromtimestamp((current_timestamp + delta).value)

    def get_current_time(self):
        return self.current_time

    def get_current_timestamp_value(self) -> Timestamp:
        return Timestamp.from_uint256(int(self.current_time.timestamp()))

    def get_current_timestamp(self) -> int:
        return int(self.current_time.timestamp())

    def get_starting_time(self):
        return self.simulation_start_time

    def get_starting_timestamp_value(self) -> Timestamp:
        return Timestamp.from_uint256(int(self.simulation_start_time.timestamp()))

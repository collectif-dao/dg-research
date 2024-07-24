from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class TimeManager:
    current_time: datetime = field(default_factory=lambda: datetime.min)

    def initialize(self):
        self.current_time = datetime.now()

    def shift_current_time(self, delta: timedelta):
        self.current_time = self.current_time + delta

    def get_current_time(self):
        return self.current_time

    def get_current_timestamp(self) -> int:
        return int(self.current_time.timestamp())

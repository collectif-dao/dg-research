from datetime import timedelta

"""
Model parameters.
"""


sys_params = {
    "timedelta_tick": timedelta(hours=3),
    "max_damage": 100_000,
}

slow_actor_max_delay = 3600 * 24 * 15
normal_actor_max_delay = 3600 * 24 * 5
quick_actor_max_delay = 3600 * 24  ## it should start from the proposal submission on the DAO level

sample_actor_delay = 3600
cancellation_delay_days = 2


class CustomDelays:
    def __init__(
        self,
        quick_max_delay: int = quick_actor_max_delay,
        normal_max_delay: int = normal_actor_max_delay,
        slow_max_delay: int = slow_actor_max_delay,
    ):
        self.quick_max_delay = quick_max_delay
        self.normal_max_delay = normal_max_delay
        self.slow_max_delay = slow_max_delay

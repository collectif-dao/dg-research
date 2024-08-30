from datetime import timedelta

"""
Model parameters.
"""


sys_params = {
    "timedelta_tick": [timedelta(hours=3)],
    "slow_actor_max_delay": 604800,
    "normal_actor_max_delay": 86400,
    "quick_actor_max_delay": 7200,
}

slow_actor_max_delay = 3600 * 24 * 15
normal_actor_max_delay = 3600 * 24 * 5
quick_actor_max_delay = 3600 * 24

sample_actor_delay = 3600

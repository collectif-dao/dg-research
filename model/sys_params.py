from datetime import timedelta

"""
Model parameters.
"""

initial_values = {
    "world_size_n_dimension": 20,
    "world_size_m_dimension": 20,
    "initial_food_sites": 5,
    "initial_predator_count": 20,
    "initial_prey_count": 20,
}

sys_params = {
    "timedelta_tick": [timedelta(hours=1)],
    "slow_actor_max_delay": 604800,
    "normal_actor_max_delay": 86400,
    "quick_actor_max_delay": 7200,
    "food_growth_rate": [3],
    "maximum_food_per_site": [10],
    "reproduction_probability": [1.0],
    "agent_lifespan": [35],
    "reproduction_food_threshold": [6],  # When the agents start reproducing
    "hunger_threshold": [15],  # When the agents start eating
    "reproduction_food": [1],  # How much food is needed for reproducing
}

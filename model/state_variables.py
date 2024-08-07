from specs.time_manager import TimeManager

from .parts.utils import *

actors = generate_actors(700, 200, 1000)
total_suply = sum([actor.st_eth_balance for actor in actors])

time_manager = TimeManager()
time_manager.initialize()

initial_state = {
    "actors": actors,
    "dg": new_dg(total_suply, time_manager),
    "time_manager": time_manager,
}

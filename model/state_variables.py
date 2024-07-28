from specs.time_manager import TimeManager

from .parts.utils import *

agents = generate_agents(700, 200, 1000)
total_suply = sum([agent["st_amount"] for agent in agents.values()])

time_manager = TimeManager()
time_manager.initialize()

initial_state = {
    "agents": generate_agents(700, 200, 1000),
    "dg": new_dg(total_suply, time_manager),
    "proposals": {},
    "proposals_new": init_proposals(time_manager),
    "time_manager": time_manager,
}

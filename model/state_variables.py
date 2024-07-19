from .parts.utils import *

agents = generate_agents(700, 200, 1000)
total_suply = sum([agent["st_amount"] for agent in agents.values()])

initial_state = {"agents": generate_agents(700, 200, 1000), "dg": new_dg(total_suply), "proposals": {}}

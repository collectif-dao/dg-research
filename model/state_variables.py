from .parts.utils import *
from .sys_params import initial_values

agents = generate_agents(700, 200, 1000)
total_suply = sum(
            [agent["st_amount"] for agent in agents.values()]
        )

initial_state = {
    'agents': generate_agents(700, 200, 1000),
    'escrow': new_escrow(total_suply),
    'proposals': {}
}

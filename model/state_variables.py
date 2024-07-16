from .parts.utils import *
from .sys_params import initial_values


initial_state = {
    'agents': generate_agents(700, 200, 1000),
    'escrow': new_escrow(),
    'proposals': {}
}

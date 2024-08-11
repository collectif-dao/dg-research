from specs.time_manager import TimeManager

from .parts.utils import *

# actors = generate_actors(700, 200, 1000)
actors = read_actors()
total_suply = sum([actor.st_eth_balance for actor in actors])

time_manager = TimeManager()
time_manager.initialize()

dg = new_dg(total_suply, time_manager)
for actor in actors:
    dg.state.signalling_escrow.lido._mint_shares(actor.address, actor.st_eth_balance)

initial_state = {
    "actors": actors,
    "dg": dg,
    "proposals_type": {},
    "time_manager": time_manager,
}

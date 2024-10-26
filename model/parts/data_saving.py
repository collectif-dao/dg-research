from collections import defaultdict
import csv

import numpy as np

from model.actors.actors import Actors
from specs.dual_governance import DualGovernance

def extract_dg_state_data(state):
    dual_governance: DualGovernance = state["dual_governance"]
    dg_state_data = {
        "dg_state_value": dual_governance.state.state.value,
        "dg_state_name": dual_governance.state.state.name,
        "dg_dynamic_timelock_seconds": dual_governance.state._calc_dynamic_timelock_duration(
            dual_governance.state.signalling_escrow.get_rage_quit_support()).to_seconds()
    }
    return dg_state_data

def timestamps_to_timesteps(*args):
    pass

def extract_proposal_data(state):
    dual_governance: DualGovernance = state["dual_governance"]

    proposals_info = dual_governance.timelock.proposals.state.proposals
    proposal_dict = defaultdict(list)
    for proposal in proposals_info:
        proposal_dict["id"].append(proposal.id)
        proposal_dict["status"].append(proposal.status)
        proposal_dict["submittedAt"].append(timestamps_to_timesteps(proposal.submittedAt))
        proposal_dict["scheduledAt"].append(timestamps_to_timesteps(proposal.scheduledAt))
        proposal_dict["executedAt"].append(timestamps_to_timesteps(proposal.executedAt))
        proposal_dict["cancelledAt"].append(timestamps_to_timesteps(proposal.cancelledAt))
    return proposal_dict

def extract_actor_data(state):
    actors: Actors = state["actors"]

    actors_dict = {
        "total_balance": np.sum(actors.stETH + actors.wstETH),
        "total_locked": np.sum(actors.stETH_locked + actors.wstETH_locked),
        "total_actors": actors.amount,
        "total_health": np.sum(actors.health)
    }
    return actors_dict

fieldnames = ["first_seal_rage_quit_support", "second_seal_rage_quit_support", "seed", "timestep", "dg_state_value", "dg_state_name", "dg_dynamic_timelock_seconds", "total_balance", "total_locked", "total_health", "total_actors"]

def save_data(params, substep, state_history, prev_state):
    # print('saving')
    timestep = prev_state["timestep"]
    if timestep == 1:
        timedata_path = prev_state["outpath"].joinpath("data.csv")
        params["timedata_file"] = open(timedata_path, "a")
        params["timedata_writer"] = csv.DictWriter(params["timedata_file"], fieldnames=fieldnames)
        params["timedata_writer"].writeheader()

    data = {
        "first_seal_rage_quit_support": prev_state["first_seal_rage_quit_support"],
        "second_seal_rage_quit_support": prev_state["second_seal_rage_quit_support"],
        "seed": prev_state["seed"],
        "timestep": timestep
    }
    data.update(extract_dg_state_data(prev_state))
    data.update(extract_actor_data(prev_state))

    params["timedata_writer"].writerow(data)

    if timestep == prev_state["n_timesteps"]:
        params["timedata_file"].close()

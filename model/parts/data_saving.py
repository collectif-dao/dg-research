from collections import defaultdict
import csv
from typing import List
from datetime import timedelta

import numpy as np

from model.actors.actor import BaseActor
from model.types.actors import ActorType
from model.types.reaction_time import ReactionTime
from specs.dual_governance import DualGovernance
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp
from specs.utils import ether_base


def extract_dg_state_data(state):
    dual_governance: DualGovernance = state["dual_governance"]
    dg_state_data = {
        "dg_state_value": dual_governance.state.state.value,
        "dg_state_name": dual_governance.state.state.name,
        "dg_dynamic_timelock_seconds": dual_governance.state._calc_dynamic_timelock_duration(
            dual_governance.state.signalling_escrow.get_rage_quit_support()).to_seconds()
    }
    return dg_state_data


def timestamps_to_timesteps(timestamp: Timestamp, starting_timestamp: Timestamp, timedelta_tick: timedelta):
    if timestamp.is_zero():
        return None
    return (timestamp - starting_timestamp).to_seconds() // int(timedelta_tick.total_seconds())


def extract_proposal_data(params, state):
    dual_governance: DualGovernance = state["dual_governance"]
    time_manager: TimeManager = state["time_manager"]
    timedelta_tick: timedelta = params["timedelta_tick"]

    simulation_start_timestamp = time_manager.get_starting_timestamp_value()
    proposals_info = dual_governance.timelock.proposals.state.proposals
    proposal_dict = defaultdict(list)
    for proposal in proposals_info:
        proposal_dict["proposal_id"].append(proposal.id)
        proposal_dict["proposal_status"].append(proposal.status)
        proposal_dict["submittedAt"].append(
            timestamps_to_timesteps(proposal.submittedAt, simulation_start_timestamp, timedelta_tick))
        proposal_dict["scheduledAt"].append(
            timestamps_to_timesteps(proposal.scheduledAt, simulation_start_timestamp, timedelta_tick))
        proposal_dict["executedAt"].append(
            timestamps_to_timesteps(proposal.executedAt, simulation_start_timestamp, timedelta_tick))
        proposal_dict["cancelledAt"].append(
            timestamps_to_timesteps(proposal.cancelledAt, simulation_start_timestamp, timedelta_tick))
        proposal_dict["unique_run_key"].append(params["unique_run_key"])
    return proposal_dict

def _extract_actor_data_by_enum(actors, enum_type, attr_name_in_actor):
    enum_actor_dict = {}
    for kind in enum_type:
        balance = 0
        locked = 0
        health = 0
        for actor in actors:
            if getattr(actor, attr_name_in_actor) == kind:
                balance += actor.st_eth_balance + actor.wstETH_balance
                locked += actor.st_eth_locked + actor.wstETH_locked
                health += actor.health
        enum_actor_dict[f"balance_{kind.name}"] = balance / ether_base
        enum_actor_dict[f"locked_{kind.name}"] = locked / ether_base
        enum_actor_dict[f"health_{kind.name}"] = health
    return enum_actor_dict


def extract_actor_data(state):
    actors: List[BaseActor] = state["actors"]

    actors_dict = {
        "total_balance": sum(actor.st_eth_balance + actor.wstETH_balance for actor in actors) / ether_base,
        "total_locked": sum(actor.st_eth_locked + actor.wstETH_locked for actor in actors) / ether_base,
        "total_health": sum(actor.health for actor in actors)
    }
    actors_dict.update(_extract_actor_data_by_enum(actors, ReactionTime, "reaction_time"))
    actors_dict.update(_extract_actor_data_by_enum(actors, ActorType, "actor_type"))

    return actors_dict


def extract_common_data(params, state):
    actors: List[BaseActor] = state["actors"]

    common_data = {key: state[key] for key in
                   ["seed", "first_seal_rage_quit_support", "second_seal_rage_quit_support"]}
    common_data["n_actors"] = len(actors)

    for reaction_time in ReactionTime:
        common_data[reaction_time.name] = 0

    for actor_type in ActorType:
        common_data[actor_type.name] = 0

    for actor in actors:
        common_data[actor.reaction_time.name] += 1
        common_data[actor.actor_type.name] += 1

    return common_data

def add_unique_run_key_to_dict(params, dict):
    dict["unique_run_key"] = params["unique_run_key"]

def save_data(params, substep, state_history, prev_state):
    timestep = prev_state["timestep"]
    if timestep == 1:
        fieldnames = ["unique_run_key", "timestep", "dg_state_value", "dg_state_name", "dg_dynamic_timelock_seconds",
                      "total_balance",
                      "total_locked", "total_health", "total_actors"]
        fieldnames += [f"{value_name}_{kind.name}"
                       for value_name in ("balance", "locked", "health")
                       for enum_type in (ReactionTime, ActorType)
                       for kind in enum_type]

        params["unique_run_key"] = 0 # This param needs to be set somewhere. Maybe in experiments/utils.py/setup_simulation from hash.
        # Maybe even remove hashes. Or calculate them here. If we are using a database, we can generate a new key using a DB from current run parameters and program version.

        common_data = extract_common_data(params, prev_state)
        add_unique_run_key_to_dict(params, common_data)
        common_data_path = prev_state["outpath"].joinpath("start_data.csv")
        with open(common_data_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=common_data.keys())
            writer.writeheader()
            writer.writerow(common_data)

        timedata_path = prev_state["outpath"].joinpath("timestep_data.csv")
        params["timedata_file"] = open(timedata_path, "a", newline="")
        params["timedata_writer"] = csv.DictWriter(params["timedata_file"], fieldnames=fieldnames)
        params["timedata_writer"].writeheader()

    timestep_data = {"timestep": timestep}
    timestep_data.update(extract_dg_state_data(prev_state))
    timestep_data.update(extract_actor_data(prev_state))
    add_unique_run_key_to_dict(params, timestep_data)

    params["timedata_writer"].writerow(timestep_data)

    if timestep == prev_state["n_timesteps"]:
        params["timedata_file"].close()

        proposal_data = extract_proposal_data(params, prev_state)
        proposal_path = prev_state["outpath"].joinpath("proposals.csv")
        with open(proposal_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(proposal_data.keys())
            writer.writerows(zip(*proposal_data.values()))

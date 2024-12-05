import logging
from collections import defaultdict
from datetime import timedelta
from typing import List

import numpy as np
import pandas as pd
from fastparquet import write
from filelock import FileLock

from model.actors.actors import Actors
from model.types.actors import ActorType
from model.types.proposals import Proposal, get_proposal_by_id
from model.types.reaction_time import ReactionTime
from specs.dual_governance import DualGovernance
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp
from specs.utils import ether_base

logging.getLogger("filelock").setLevel(logging.WARNING)

# fieldnames = [
#     "unique_run_key",
#     "timestep",
#     "dg_state_value",
#     "dg_state_name",
#     "dg_dynamic_timelock_seconds",
#     "total_balance",
#     "total_locked",
#     "total_health",
#     "total_actors",
#     "total_actors_locked",
#     "total_actors_affected",
#     "total_actors_quit",
# ]
# fieldnames += [
#     f"{value_name}_{kind.name}"
#     for value_name in ("balance", "locked", "health", "actors_locked", "actors_affected", "actors_quit")
#     for enum_type in (ReactionTime, ActorType)
#     for kind in enum_type
# ]


def extract_dg_state_data(state):
    dual_governance: DualGovernance = state["dual_governance"]
    dg_state_data = {
        "dg_state_value": dual_governance.state.state.value,
        "dg_state_name": dual_governance.state.state.name,
        "dg_rage_quit_support": dual_governance.state.signalling_escrow.get_rage_quit_support(),
        "dg_dynamic_timelock_seconds": dual_governance.state._calc_dynamic_timelock_duration(
            dual_governance.state.signalling_escrow.get_rage_quit_support()
        ).to_seconds(),
    }
    return dg_state_data


def timestamps_to_timesteps(timestamp: Timestamp, starting_timestamp: Timestamp, timedelta_tick: timedelta):
    if timestamp.is_zero():
        return 0

    return (timestamp - starting_timestamp).to_seconds() // int(timedelta_tick.total_seconds())


def extract_proposal_data(params, state):
    dual_governance: DualGovernance = state["dual_governance"]
    time_manager: TimeManager = state["time_manager"]
    timedelta_tick: timedelta = params["timedelta_tick"]
    proposals: List[Proposal] = state["proposals"]

    simulation_start_timestamp = time_manager.get_starting_timestamp_value()
    proposals_info = dual_governance.timelock.proposals.state.proposals

    if not proposals_info:
        return None

    proposal_dict = defaultdict(list)

    for proposal in proposals_info:
        model_proposal = get_proposal_by_id(proposals, proposal.id)
        if model_proposal is None:
            continue

        proposal_dict["proposal_id"].append(proposal.id)
        proposal_dict["proposals_status_value"].append(proposal.status.value)
        proposal_dict["proposals_status_name"].append(proposal.status.name)
        proposal_dict["proposal_damage"].append(model_proposal.damage)
        proposal_dict["proposal_type_value"].append(model_proposal.proposal_type.value)
        proposal_dict["proposal_type_name"].append(model_proposal.proposal_type.name)
        proposal_dict["submittedAt"].append(
            timestamps_to_timesteps(proposal.submittedAt, simulation_start_timestamp, timedelta_tick)
        )
        proposal_dict["scheduledAt"].append(
            timestamps_to_timesteps(proposal.scheduledAt, simulation_start_timestamp, timedelta_tick)
        )
        proposal_dict["executedAt"].append(
            timestamps_to_timesteps(proposal.executedAt, simulation_start_timestamp, timedelta_tick)
        )
        proposal_dict["cancelledAt"].append(
            timestamps_to_timesteps(proposal.cancelledAt, simulation_start_timestamp, timedelta_tick)
        )

        effects_labels = []
        effects_damages = []

        for label, value in model_proposal.effects.effects.items():
            effects_labels.append(label)
            effects_damages.append(value)

        proposal_dict["proposal_effects_labels"].append(effects_labels)
        proposal_dict["proposal_effects_damages"].append(effects_damages)

    proposal_dict["simulation_hash"] = state["simulation_hash"]

    return proposal_dict


def _extract_actor_data_by_enum(actors: Actors, enum_type, attr_name_in_actor):
    enum_actor_dict = {}

    for kind in enum_type:
        mask = getattr(actors, attr_name_in_actor) == kind.value

        balance = np.sum(actors.stETH[mask] + actors.wstETH[mask]) / ether_base
        hypothetical_balance = np.sum(actors.hypothetical_stETH[mask] + actors.hypothetical_wstETH[mask]) / ether_base
        locked = np.sum(actors.stETH_locked[mask] + actors.wstETH_locked[mask]) / ether_base
        health = np.sum(actors.health[mask])
        cropped_health = np.sum(actors.cropped_health[mask])
        hypothetical_health = np.sum(actors.hypothetical_health[mask])
        damage = np.sum(actors.total_damage[mask])
        healing = np.sum(actors.total_healing[mask])
        recovery = np.sum(actors.total_recovery[mask])
        actors_locked = np.count_nonzero(actors.stETH_locked[mask] + actors.wstETH_locked[mask])
        actors_affected = np.sum((actors.health[mask] <= 0) + (actors.hypothetical_health[mask] <= 0))
        actors_quit = np.count_nonzero(actors.did_quit[mask])
        quit = np.sum(actors.stETH[actors.did_quit & mask] + actors.wstETH[actors.did_quit & mask]) / ether_base

        enum_actor_dict[f"balance_{kind.name}"] = balance
        enum_actor_dict[f"hypothetical_balance{kind.name}"] = hypothetical_balance
        enum_actor_dict[f"locked_{kind.name}"] = locked
        enum_actor_dict[f"health_{kind.name}"] = health
        enum_actor_dict[f"hypothetical_health_{kind.name}"] = hypothetical_health
        enum_actor_dict[f"cropped_health_{kind.name}"] = cropped_health
        enum_actor_dict[f"damage_{kind.name}"] = damage
        enum_actor_dict[f"healing_{kind.name}"] = healing
        enum_actor_dict[f"recovery_{kind.name}"] = recovery
        enum_actor_dict[f"actors_locked_{kind.name}"] = actors_locked
        enum_actor_dict[f"actors_affected_{kind.name}"] = actors_affected
        enum_actor_dict[f"actors_quit_{kind.name}"] = actors_quit
        enum_actor_dict[f"quit_{kind.name}"] = quit

    return enum_actor_dict


def extract_actor_data(state):
    actors: Actors = state["actors"]

    total_stETH = np.sum(actors.stETH)
    total_wstETH = np.sum(actors.wstETH)
    total_stETH_locked = np.sum(actors.stETH_locked)
    total_wstETH_locked = np.sum(actors.wstETH_locked)

    total_balance = (total_stETH + total_wstETH) / ether_base
    total_locked = (total_stETH_locked + total_wstETH_locked) / ether_base
    total_actors_locked = np.count_nonzero(actors.stETH_locked + actors.wstETH_locked)
    total_actors_affected = np.sum((actors.health <= 0) + (actors.hypothetical_health <= 0))
    total_actors_quit = np.count_nonzero(actors.did_quit)
    total_quit = np.sum(actors.stETH[actors.did_quit] + actors.wstETH[actors.did_quit]) / ether_base

    actors_dict = {
        "actors_total_balance": total_balance,
        "actors_total_locked": total_locked,
        "actors_total_number": actors.amount,
        "actors_total_number_locked": total_actors_locked,
        "actors_total_health": np.sum(actors.health),
        "actors_total_hypothetical_health": np.sum(actors.hypothetical_health),
        "actors_total_cropped_health": np.sum(actors.cropped_health),
        "actors_total_damage": np.sum(actors.total_damage),
        "actors_total_healing": np.sum(actors.total_healing),
        "actors_total_recovery": np.sum(actors.total_recovery),
        "actors_total_actors_locked": total_actors_locked,
        "actors_total_actors_affected": total_actors_affected,
        "actors_total_actors_quit": total_actors_quit,
        "actors_total_quit": total_quit,
    }
    actors_dict.update(_extract_actor_data_by_enum(actors, ReactionTime, "reaction_time"))
    actors_dict.update(_extract_actor_data_by_enum(actors, ActorType, "actor_type"))

    return actors_dict


def extract_common_data(params, state):
    actors: Actors = state["actors"]

    common_data = {
        key: state[key]
        for key in [
            "seed",
            "first_seal_rage_quit_support",
            "second_seal_rage_quit_support",
            "attacker_funds",
            "simulation_hash",
            "determining_factor",
        ]
    }
    common_data["n_actors"] = actors.amount

    for reaction_time in ReactionTime:
        common_data[reaction_time.name] = np.count_nonzero(actors.reaction_time == reaction_time.value)

    for actor_type in ActorType:
        common_data[actor_type.name] = np.count_nonzero(actors.actor_type == actor_type.value)

    return common_data


def save_data(params, substep, state_history, prev_state):
    timestep = prev_state["timestep"]

    timestep_data = {"timestep": timestep, "simulation_hash": prev_state["simulation_hash"]}
    timestep_data.update(extract_dg_state_data(prev_state))
    timestep_data.update(extract_actor_data(prev_state))

    if timestep == prev_state["n_timesteps"]:
        proposal_data = extract_proposal_data(params, prev_state)
        common_data = extract_common_data(params, prev_state)

        return {"save_data": (common_data, timestep_data, proposal_data)}
    else:
        return {"save_data": (None, timestep_data, None)}


def write_data_fastparquet(params, substep, state_history, prev_state, policy_input):
    (common_data, new_timestep_data, proposal_data) = policy_input["save_data"]
    timestep = prev_state["timestep"]

    timestep_data = prev_state["timestep_data"]
    if timestep == 1:
        for key, val in new_timestep_data.items():
            timestep_data[key] = [val]
    else:
        for key, val in new_timestep_data.items():
            timestep_data[key].append(val)

    if timestep == prev_state["n_timesteps"]:
        combined_df = pd.DataFrame(timestep_data)
        parquet_path = prev_state["outpath"].joinpath("timestep_data.parquet")
        lock_path = prev_state["outpath"].joinpath("timestep_data.lock")
        lock = FileLock(lock_path, timeout=30)
        try:
            if timestep_data:
                with lock:
                    write(
                        str(parquet_path), combined_df, append=parquet_path.exists(), compression="SNAPPY", stats=False
                    )
        except Exception as e:
            print(f"Error while saving timestep data: {e}")
            raise

        try:
            if common_data:
                common_data_df = pd.DataFrame([common_data])
                common_data_path = prev_state["outpath"].joinpath("common_data.parquet")
                common_data_lock_path = prev_state["outpath"].joinpath("common_data.lock")
                common_data_lock = FileLock(common_data_lock_path, timeout=30)
                with common_data_lock:
                    write(
                        str(common_data_path),
                        common_data_df,
                        append=common_data_path.exists(),
                        compression="SNAPPY",
                        stats=False,
                    )

            if proposal_data is not None:
                proposal_data_df = pd.DataFrame(proposal_data)
                proposal_data_path = prev_state["outpath"].joinpath("proposals_data.parquet")
                proposal_lock_path = prev_state["outpath"].joinpath("proposals_data.lock")
                proposal_lock = FileLock(proposal_lock_path, timeout=30)

                with proposal_lock:
                    write(
                        str(proposal_data_path),
                        proposal_data_df,
                        append=proposal_data_path.exists(),
                        compression="SNAPPY",
                        stats=False,
                    )
        except Exception as e:
            print(f"Error while saving data: {e}")
            raise

        return ("timestep_data", timestep_data)

    return ("timestep_data", timestep_data)

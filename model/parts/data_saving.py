import logging
from collections import defaultdict
from datetime import timedelta

import numpy as np
import pandas as pd
from fastparquet import write
from filelock import FileLock

from model.actors.actors import Actors
from model.types.actors import ActorType
from model.types.reaction_time import ReactionTime
from specs.dual_governance import DualGovernance
from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp
from specs.utils import ether_base

logging.getLogger("filelock").setLevel(logging.WARNING)

fieldnames = [
    "unique_run_key",
    "timestep",
    "dg_state_value",
    "dg_state_name",
    "dg_dynamic_timelock_seconds",
    "total_balance",
    "total_locked",
    "total_health",
    "total_actors",
]
fieldnames += [
    f"{value_name}_{kind.name}"
    for value_name in ("balance", "locked", "health")
    for enum_type in (ReactionTime, ActorType)
    for kind in enum_type
]


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

    simulation_start_timestamp = time_manager.get_starting_timestamp_value()
    proposals_info = dual_governance.timelock.proposals.state.proposals
    proposal_dict = defaultdict(list)
    for proposal in proposals_info:
        proposal_dict["proposal_id"].append(proposal.id)
        proposal_dict["proposals_status_value"].append(proposal.status.value)
        proposal_dict["proposals_status_name"].append(proposal.status.name)
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

    proposal_dict["simulation_hash"] = state["simulation_hash"]

    return proposal_dict


def _extract_actor_data_by_enum(actors: Actors, enum_type, attr_name_in_actor):
    enum_actor_dict = {}

    for kind in enum_type:
        mask = getattr(actors, attr_name_in_actor) == kind.value

        balance = np.sum(actors.stETH[mask] + actors.wstETH[mask])
        locked = np.sum(actors.stETH_locked[mask] + actors.wstETH_locked[mask])
        health = np.sum(actors.health[mask])

        enum_actor_dict[f"balance_{kind.name}"] = balance / ether_base
        enum_actor_dict[f"locked_{kind.name}"] = locked / ether_base
        enum_actor_dict[f"health_{kind.name}"] = health

    return enum_actor_dict


def extract_actor_data(state):
    actors: Actors = state["actors"]

    total_stETH = np.sum(actors.stETH)
    total_wstETH = np.sum(actors.wstETH)
    total_stETH_locked = np.sum(actors.stETH_locked)
    total_wstETH_locked = np.sum(actors.wstETH_locked)

    total_balance = (total_stETH + total_wstETH) / ether_base
    total_locked = (total_stETH_locked + total_wstETH_locked) / ether_base

    actors_dict = {
        "actors_total_balance": total_balance,
        "actors_total_locked": total_locked,
        "actors_total_number": actors.amount,
        "actors_total_health": np.sum(actors.health),
    }
    actors_dict.update(_extract_actor_data_by_enum(actors, ReactionTime, "reaction_time"))
    actors_dict.update(_extract_actor_data_by_enum(actors, ActorType, "actor_type"))

    return actors_dict


def extract_common_data(params, state):
    actors: Actors = state["actors"]

    common_data = {
        key: state[key]
        for key in ["seed", "first_seal_rage_quit_support", "second_seal_rage_quit_support", "simulation_hash"]
    }
    common_data["n_actors"] = actors.amount

    for reaction_time in ReactionTime:
        common_data[reaction_time.name] = np.count_nonzero(actors.reaction_time == reaction_time.value)

    for actor_type in ActorType:
        common_data[actor_type.name] = np.count_nonzero(actors.actor_type == actor_type.value)

    return common_data


def save_data(params, substep, state_history, prev_state):
    timestep = prev_state["timestep"]
    common_data_df = None

    if timestep == 1:
        common_data = extract_common_data(params, prev_state)
        common_data_df = pd.DataFrame([common_data])

    timestep_data = {"timestep": timestep, "simulation_hash": prev_state["simulation_hash"]}
    timestep_data.update(extract_dg_state_data(prev_state))
    timestep_data.update(extract_actor_data(prev_state))
    timestep_data_df = pd.DataFrame([timestep_data])

    if timestep == prev_state["n_timesteps"]:
        proposal_data = {}
        proposal_data = extract_proposal_data(params, prev_state)
        proposal_data_df = pd.DataFrame(proposal_data)

        return {"save_data": (common_data_df, timestep_data_df, proposal_data_df)}
    else:
        return {"save_data": (common_data_df, timestep_data_df, None)}


def save_common_dataframe(params, substep, state_history, prev_state, policy_input):
    (common_data_df, _, proposal_data_df) = policy_input["save_data"]
    timestep = prev_state["timestep"]
    parquet_path = prev_state["outpath"].joinpath("common_data.parquet")
    lock_path = prev_state["outpath"].joinpath("timestep_data.lock")

    if timestep != 1:
        return ("common_dataframe", prev_state["common_dataframe"])

    if timestep == prev_state["n_timesteps"]:
        lock = FileLock(lock_path)
        try:
            with lock:
                common_data_df = prev_state["common_dataframe"]
                if parquet_path.exists() and parquet_path.stat().st_size > 0:
                    existing_df = pd.read_parquet(parquet_path)
                    common_data_df = pd.concat([existing_df, common_data_df], ignore_index=True)

                common_data_df.to_parquet(parquet_path, index=False)
                common_data_df = pd.DataFrame()

                if proposal_data_df is not None:
                    proposal_path = prev_state["outpath"].joinpath("proposals_data.parquet")
                    proposal_lock_path = prev_state["outpath"].joinpath("proposals_data.lock")
                    proposal_lock = FileLock(proposal_lock_path)

                    with proposal_lock:
                        if proposal_path.exists() and proposal_path.stat().st_size > 0:
                            existing_df = pd.read_parquet(proposal_path)
                            proposal_data_df = pd.concat([existing_df, proposal_data_df], ignore_index=True)
                        proposal_data_df.to_parquet(proposal_path, index=False)

        except Exception as e:
            print(f"Error while saving data: {e}")
            raise

    return ("common_dataframe", common_data_df)


def save_timestep_dataframe(params, substep, state_history, prev_state, policy_input):
    (_, timestep_data_df, _) = policy_input["save_data"]
    timestep = prev_state["timestep"]
    parquet_path = prev_state["outpath"].joinpath("timestep_data.parquet")
    lock_path = prev_state["outpath"].joinpath("timestep_data.lock")

    combined_df = pd.concat([prev_state["timestep_dataframe"], timestep_data_df], ignore_index=True)

    if timestep == prev_state["n_timesteps"]:
        lock = FileLock(lock_path)
        try:
            with lock:
                if parquet_path.exists() and parquet_path.stat().st_size > 0:
                    existing_df = pd.read_parquet(parquet_path)
                    combined_df = pd.concat([existing_df, combined_df], ignore_index=True)

                combined_df.to_parquet(parquet_path, index=False)
                combined_df = pd.DataFrame()

        except Exception as e:
            print(f"Error while saving timestep data: {e}")
            raise

    return ("timestep_dataframe", combined_df)


def save_common_dataframe_fastparquet(params, substep, state_history, prev_state, policy_input):
    (common_data_df, _, proposal_data_df) = policy_input["save_data"]
    timestep = prev_state["timestep"]
    parquet_path = prev_state["outpath"].joinpath("common_data.parquet")
    lock_path = prev_state["outpath"].joinpath("common_data.lock")

    if timestep != 1 and timestep != prev_state["n_timesteps"]:
        return ("common_dataframe", prev_state["common_dataframe"])

    if timestep == 1:
        return ("common_dataframe", common_data_df)

    if timestep == prev_state["n_timesteps"]:
        lock = FileLock(lock_path, timeout=30)
        try:
            with lock:
                if prev_state["common_dataframe"] is not None and not prev_state["common_dataframe"].empty:
                    write(
                        str(parquet_path),
                        prev_state["common_dataframe"],
                        append=parquet_path.exists(),
                        compression="SNAPPY",
                    )

                if proposal_data_df is not None:
                    proposal_path = prev_state["outpath"].joinpath("proposals_data.parquet")
                    proposal_lock_path = prev_state["outpath"].joinpath("proposals_data.lock")
                    proposal_lock = FileLock(proposal_lock_path, timeout=30)

                    with proposal_lock:
                        write(
                            str(proposal_path),
                            proposal_data_df,
                            append=proposal_path.exists(),
                            compression="SNAPPY",
                        )

        except Exception as e:
            print(f"Error while saving data: {e}")
            raise
        finally:
            # Clean up
            if "common_data_df" in locals():
                del common_data_df
            if "proposal_data_df" in locals():
                del proposal_data_df

    return ("common_dataframe", pd.DataFrame())


def save_timestep_dataframe_fastparquet(params, substep, state_history, prev_state, policy_input):
    (_, timestep_data_df, _) = policy_input["save_data"]
    timestep = prev_state["timestep"]
    parquet_path = prev_state["outpath"].joinpath("timestep_data.parquet")
    lock_path = prev_state["outpath"].joinpath("timestep_data.lock")

    combined_df = pd.concat([prev_state["timestep_dataframe"], timestep_data_df], ignore_index=True)

    if timestep == prev_state["n_timesteps"]:
        lock = FileLock(lock_path, timeout=30)
        try:
            with lock:
                if combined_df is not None and not combined_df.empty:
                    write(
                        str(parquet_path),
                        combined_df,
                        append=parquet_path.exists(),
                        compression="SNAPPY",
                    )

        except Exception as e:
            print(f"Error while saving timestep data: {e}")
            raise
        finally:
            if "combined_df" in locals():
                del combined_df
                combined_df = pd.DataFrame()

            if "timestep_data_df" in locals():
                del timestep_data_df

        return ("timestep_dataframe", pd.DataFrame())

    return ("timestep_dataframe", combined_df)

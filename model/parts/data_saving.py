from collections import defaultdict
from datetime import timedelta

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from model.actors.actors import Actors
from specs.dual_governance import DualGovernance
from specs.types.timestamp import Timestamp
from specs.utils import ether_base


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


def timestamps_to_timesteps(timestamp: Timestamp, starting_time: int, timedelta_tick: timedelta):
    if timestamp.value != 0:
        time_now = 1 + (timestamp.value - starting_time) / int(timedelta_tick.total_seconds())
        return int(time_now)
    else:
        return None


def extract_proposal_data(state, params):
    dual_governance: DualGovernance = state["dual_governance"]
    simulation_starting_time: int = state["simulation_starting_time"]
    timedelta_tick: timedelta = params["timedelta_tick"]

    proposals_info = dual_governance.timelock.proposals.state.proposals
    proposal_dict = defaultdict(list)

    for proposal in proposals_info:
        proposal_dict["proposals_id"].append(proposal.id)
        proposal_dict["proposals_status_value"].append(proposal.status.value)
        proposal_dict["proposals_status_name"].append(proposal.status.name)
        proposal_dict["proposals_submittedAt"].append(
            timestamps_to_timesteps(proposal.submittedAt, simulation_starting_time, timedelta_tick)
        )
        proposal_dict["proposals_scheduledAt"].append(
            timestamps_to_timesteps(proposal.scheduledAt, simulation_starting_time, timedelta_tick)
        )
        proposal_dict["proposals_executedAt"].append(
            timestamps_to_timesteps(proposal.executedAt, simulation_starting_time, timedelta_tick)
        )

    return proposal_dict


def extract_actor_data(state):
    actors: Actors = state["actors"]

    total_locked = np.sum(actors.stETH_locked + actors.wstETH_locked) / ether_base
    total_balance = np.sum(actors.stETH + actors.wstETH) / ether_base

    actors_dict = {
        "actors_total_balance": total_balance,
        "actors_total_locked": total_locked,
        "actors_total_number": actors.amount,
        "actors_total_health": np.sum(actors.health),
    }
    return actors_dict


fieldnames = [
    "first_seal_rage_quit_support",
    "second_seal_rage_quit_support",
    "seed",
    "timestep",
    "dg_state_value",
    "dg_state_name",
    "dg_dynamic_timelock_seconds",
    "total_balance",
    "total_locked",
    "total_health",
    "total_actors",
]


def save_data(params, substep, state_history, prev_state):
    timestep = prev_state["timestep"]
    parquet_path = prev_state["outpath"].joinpath("data.parquet")

    # Prepare the data for saving
    data = {
        "first_seal_rage_quit_support": prev_state["first_seal_rage_quit_support"],
        "second_seal_rage_quit_support": prev_state["second_seal_rage_quit_support"],
        "seed": prev_state["seed"],
        "timestep": timestep,
    }
    data.update(extract_dg_state_data(prev_state))
    data.update(extract_actor_data(prev_state))
    data.update(extract_proposal_data(prev_state, params))

    # Convert the data to a DataFrame
    df = pd.DataFrame([data])

    # Write to Parquet file
    if not parquet_path.exists():
        df.to_parquet(parquet_path, index=False)
    else:
        # Append to the existing Parquet file
        existing_df = pq.read_table(parquet_path).to_pandas()
        updated_df = pd.concat([existing_df, df], ignore_index=True)
        updated_df.to_parquet(parquet_path, index=False)

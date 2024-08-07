import random
import uuid
from typing import *

import matplotlib.pyplot as plt
import numpy as np

from model.actors.actor import BaseActor
from model.actors.st_holder_actor import StHolderActor
from specs.dual_governance import DualGovernance
from specs.dual_governance.proposals import Proposals
from specs.dual_governance.state import DualGovernanceState, State
from specs.lido import Lido
from specs.time_manager import TimeManager
from specs.utils import ether_base


# Initialization
def new_agent(st: float, prob: float) -> dict:
    agent = {
        "st_amount": st * ether_base,
        "prob": prob,
    }
    return agent


def generate_agents(mean_st: float, std_st: float, count: int) -> Dict[str, dict]:
    initial_agents = {}
    st_distrib = np.random.normal(mean_st, std_st, count)
    for amount in st_distrib:
        created_agent = new_agent(amount, random.random() / 10)
        initial_agents[uuid.uuid4()] = created_agent
    return initial_agents


def generate_actors(mean_st: float, std_st: float, count: int) -> List[BaseActor]:
    initial_actors = []
    st_distrib = np.random.normal(mean_st, std_st, count)
    for amount in st_distrib:
        created_actor = StHolderActor()
        created_actor.initialize(0, amount * ether_base)
        initial_actors.append(created_actor)
    return initial_actors


def new_dg(total_suply, time_manager: TimeManager) -> DualGovernanceState:
    dg = DualGovernance()

    lido = Lido(total_shares=total_suply, total_supply=total_suply)
    lido.set_buffered_ether(total_suply)

    dg.initialize("", time_manager, lido)
    return dg


def new_proposal(timestep: int) -> dict:
    proposal = {"prob": random.random(), "timestep": timestep}
    return proposal


def init_proposals(time_manager: TimeManager):
    proposals = Proposals()
    proposals.initialize(time_manager)
    return proposals


# plotting
def aggregate_runs(df, aggregate_dimension):
    df_copy = df.copy()
    df_copy = df_copy.drop(columns=["current_time"])
    mean_df = df_copy.groupby(aggregate_dimension).mean().reset_index()
    median_df = df_copy.groupby(aggregate_dimension).median().reset_index()
    std_df = df_copy.groupby(aggregate_dimension).std().reset_index()
    min_df = df_copy.groupby(aggregate_dimension).min().reset_index()

    mean_df.loc[:, "current_time"] = df["current_time"]
    median_df.loc[:, "current_time"] = df["current_time"]
    std_df.loc[:, "current_time"] = df["current_time"]
    min_df.loc[:, "current_time"] = df["current_time"]
    return mean_df, median_df, std_df, min_df


def monte_carlo_plot(df, aggregate_dimension, x, y, runs):
    """
    A function that generates timeseries plot of Monte Carlo runs.

    Parameters:
    df: dataframe name
    aggregate_dimension: the dimension you would like to aggregate on, the standard one is timestep.
    x = x axis variable for plotting
    y = y axis variable for plotting
    run_count = the number of monte carlo simulations

    Example run:
    monte_carlo_plot(df,'timestep','timestep','revenue',run_count=100)
    """
    mean_df, median_df, std_df, min_df = aggregate_runs(df, aggregate_dimension)
    plt.figure(figsize=(10, 6))
    for r in range(1, runs + 1):
        legend_name = "Run " + str(r)
        plt.plot(df[df.run == r][x], df[df.run == r][y], label=legend_name)
    plt.plot(mean_df[x], mean_df[y], label="Mean", color="black")
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
    plt.xlabel(x)
    plt.ylabel(y)
    title_text = "Performance of " + y + " over " + str(runs) + " Monte Carlo Runs"
    plt.title(title_text)


def state_plot(df, x, y, run):
    states = df[df.run == run][y].map(lambda r: State(r).name)
    states.value_counts().plot(kind="bar").set_title("DG states time")
    plt.figure(figsize=(10, 6))
    plt.plot(df[df.run == run][x], states)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.title("DG States")
    plt.show()

import random
import uuid
from typing import *

import matplotlib.pyplot as plt
import numpy as np

from specs.escrow.escrow import Escrow


# Initialization
def new_agent(st: float, prob: float) -> dict:
    agent = {
        "st_amount": st,
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


def new_escrow(total_suply) -> Escrow:
    escrow = Escrow()
    escrow.initialize("", total_suply)
    return escrow


def new_proposal(timestep: int) -> dict:
    proposal = {"prob": random.random(), "timestep": timestep}
    return proposal


# plotting
def aggregate_runs(df, aggregate_dimension):
    """
    Function to aggregate the monte carlo runs along a single dimension.

    Parameters:
    df: dataframe name
    aggregate_dimension: the dimension you would like to aggregate on, the standard one is timestep.

    Example run:
    mean_df,median_df,std_df,min_df = aggregate_runs(df,'timestep')
    """

    mean_df = df.groupby(aggregate_dimension).mean().reset_index()
    median_df = df.groupby(aggregate_dimension).median().reset_index()
    std_df = df.groupby(aggregate_dimension).std().reset_index()
    min_df = df.groupby(aggregate_dimension).min().reset_index()

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
        plt.plot(df[df.run == r].timestep, df[df.run == r][y], label=legend_name)
    plt.plot(mean_df[x], mean_df[y], label="Mean", color="black")
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
    plt.xlabel(x)
    plt.ylabel(y)
    title_text = "Performance of " + y + " over " + str(runs) + " Monte Carlo Runs"
    plt.title(title_text)

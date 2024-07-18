import pandas as pd
from .parts.utils import *
from radcad import Model, Simulation, Experiment

from .state_variables import initial_state
from .state_update_blocks import state_update_blocks
from .sys_params import sys_params


def run():
    """
    Definition:
    Run simulation
    """
    model = Model(
        # Model initial state
        initial_state=initial_state,
        # Model Partial State Update Blocks
        state_update_blocks=state_update_blocks,
        # System Parameters
        params=sys_params,
    )

    simulation = Simulation(
        model=model,
        timesteps=300,  # Number of timesteps
        runs=3,  # Number of Monte Carlo Runs
    )

    # Executes the simulation, and returns the raw results
    result = simulation.run()

    df = pd.DataFrame(result)

    return df

def postprocessingNew(df):
    # subset to last substep
    df = df[df['substep'] == df.substep.max()]

    # Get the ABM results
    agent_ds = df.agents
    proposals_ds = df.proposals
    escrow_ds = df.escrow
    timesteps = df.timestep

    proposals_count = proposals_ds.map(lambda s: sum([1 for proposal in s.values()]))

    st_at_agents = agent_ds.map(
        lambda s: sum(
            [agent["st_amount"] for agent in s.values()]
        )
    )

    st_in_escrow = escrow_ds.map(
        lambda s: s.staked_stETH
    )

    # Create an analysis dataset
    data = (pd.DataFrame({'timestep': timesteps,
                          'run': df.run,
                          'proposals_count': proposals_count,
                          'st_at_agents':st_at_agents,
                          'st_in_escrow':st_in_escrow})       
           )
    
    return data

def postprocessing(df):
    """
    Definition:
    Refine and extract metrics from the simulation

    Parameters:
    df: simulation dataframe
    """
    # subset to last substep
    df = df[df["substep"] == df.substep.max()]

    # Get the ABM results
    agent_ds = df.agents
    site_ds = df.sites
    timesteps = df.timestep

    # Get metrics

    ## Agent quantity
    prey_count = agent_ds.map(
        lambda s: sum([1 for agent in s.values() if agent["type"] == "prey"])
    )
    predator_count = agent_ds.map(
        lambda s: sum([1 for agent in s.values() if agent["type"] == "predator"])
    )

    ## Food quantity
    food_at_sites = site_ds.map(lambda s: s.sum())
    food_at_prey = agent_ds.map(
        lambda s: sum(
            [agent["food"] for agent in s.values() if agent["type"] == "prey"]
        )
    )
    food_at_predators = agent_ds.map(
        lambda s: sum(
            [agent["food"] for agent in s.values() if agent["type"] == "predator"]
        )
    )

    ## Food metrics
    median_site_food = site_ds.map(lambda s: np.median(s))
    median_prey_food = agent_ds.map(
        lambda s: np.median(
            [agent["food"] for agent in s.values() if agent["type"] == "prey"]
        )
    )
    median_predator_food = agent_ds.map(
        lambda s: np.median(
            [agent["food"] for agent in s.values() if agent["type"] == "predator"]
        )
    )

    ## Age metrics
    prey_median_age = agent_ds.map(
        lambda s: np.median(
            [agent["age"] for agent in s.values() if agent["type"] == "prey"]
        )
    )
    predator_median_age = agent_ds.map(
        lambda s: np.median(
            [agent["age"] for agent in s.values() if agent["type"] == "predator"]
        )
    )

    # Create an analysis dataset
    data = pd.DataFrame(
        {
            "timestep": timesteps,
            "run": df.run,
            "prey_count": prey_count,
            "predator_count": predator_count,
            "food_at_sites": food_at_sites,
            "food_at_prey": food_at_prey,
            "food_at_predators": food_at_predators,
            "median_site_food": median_site_food,
            "median_prey_food": median_prey_food,
            "median_predator_food": median_predator_food,
            "prey_median_age": prey_median_age,
            "predator_median_age": predator_median_age,
        }
    )

    return data

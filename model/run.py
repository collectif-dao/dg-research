import pandas as pd
from radcad import Model, Simulation

from .parts.utils import *
from .state_update_blocks import state_update_blocks
from .state_variables import initial_state
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


def postprocessing(df):
    # subset to last substep
    df = df[df["substep"] == df.substep.max()]

    # Get the ABM results
    agent_ds = df.agents
    proposals_ds = df.proposals
    dg_ds = df.dg
    time_manager_ds = df.time_manager
    timesteps = df.timestep

    proposals_count = proposals_ds.map(lambda s: sum([1 for proposal in s.values()]))

    st_at_agents = agent_ds.map(lambda s: sum([agent["st_amount"] for agent in s.values()]))

    # st_in_escrow = dg_ds.map(lambda s: s.signalling_escrow.staked_stETH)

    current_time = time_manager_ds.map(lambda s: s.current_time)

    dg_state = dg_ds.map(lambda s: int(s.state.state.value))

    rqs = dg_ds.map(lambda s: int(s.state.signalling_escrow.get_rage_quit_support()))

    # Create an analysis dataset
    data = pd.DataFrame(
        {
            "timestep": timesteps,
            "run": df.run,
            "proposals_count": proposals_count,
            "st_at_agents": st_at_agents,
            # "st_in_escrow": st_in_escrow,
            "dg_state": dg_state,
            "current_time": current_time,
            "rqs": rqs,
        }
    )

    return data

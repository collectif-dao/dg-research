import pandas as pd
from radcad import Model, Simulation

from model.state_update_blocks import state_update_blocks
from model.sys_params import sys_params
from model.types.scenario import Scenario
from model.utils.initialization import generate_initial_state


def run():
    """
    Definition:
    Run simulation
    """
    state = generate_initial_state(Scenario.HappyPath)

    model = Model(
        initial_state=state,
        state_update_blocks=state_update_blocks,
        params=sys_params,
    )

    simulation = Simulation(
        model=model,
        timesteps=300,  # Number of timesteps
        runs=1,  # Number of Monte Carlo Runs
    )

    result = simulation.run()

    df = pd.DataFrame(result)

    return df

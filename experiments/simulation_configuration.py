from datetime import datetime, timedelta
from pathlib import Path

from model.sys_params import sys_params


def get_path() -> Path:
    out_path = Path("results/simulations")
    out_path.mkdir(exist_ok=True)

    return out_path


MONTE_CARLO_RUNS = 1  # number of runs

timedelta_per_timestep = sys_params["timedelta_tick"]  # delta time per timestep
days_per_month = 30
timesteps_per_day = int(timedelta(hours=24) / timedelta_per_timestep)
SIMULATION_TIME_MONTHS = 1  # number of months model is simulating
TIMESTEPS = int((timesteps_per_day * days_per_month) * SIMULATION_TIME_MONTHS)  # number of simulation timesteps
SIMULATION_TIME = datetime(2024, 9, 1)  # simulation starting time


def calculate_timesteps(simulation_months: float = 1) -> int:
    timesteps = int((timesteps_per_day * days_per_month) * simulation_months)

    return timesteps

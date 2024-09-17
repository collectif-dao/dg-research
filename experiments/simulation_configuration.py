from datetime import datetime, timedelta
from pathlib import Path


def get_path() -> Path:
    out_path = Path("results/simulations")
    out_path.mkdir(exist_ok=True)

    return out_path


MONTE_CARLO_RUNS = 1  # number of runs

DELTA_TIME = timedelta(hours=3)  # delta time per timestep
days_per_month = 30
timesteps_per_day = timedelta(hours=24) / DELTA_TIME
SIMULATION_TIME_MONTHS = 1  # number of months model is simulating
TIMESTEPS = int((timesteps_per_day * days_per_month) * SIMULATION_TIME_MONTHS)  # number of simulation timesteps
SIMULATION_TIME = datetime(2024, 9, 1)  # simulation starting time


def calculate_timesteps(simulation_months: int = 1) -> int:
    timesteps = int((timesteps_per_day * days_per_month) * simulation_months)

    return timesteps

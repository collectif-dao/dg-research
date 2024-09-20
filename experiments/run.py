import argparse
import logging
import sys
import time

from radcad import Backend, Engine

from experiments.simulation_configuration import get_path
from experiments.templates.model_validation import create_experiment as model_validation_experiment
from experiments.templates.rage_quit_scenario import create_experiment as rage_quit_experiment
from experiments.templates.withdrawal_queue_replacement import create_experiment as withdrawal_queue_experiment
from experiments.templates.withdrawal_queue_replacement_institutional import create_experiment as withdrawal_queue_replacement_institutional
from experiments.utils import (
    merge_simulation_results,
    save_combined_actors_simulation_result,
    save_postprocessing_result,
)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def run(simulation_name: str = None):
    out_path = get_path()

    if simulation_name is None:
        simulation_name = "model_validation"

    simulations = {
        "model_validation": model_validation_experiment,
        "withdrawal_queue_replacement": withdrawal_queue_experiment,
        "rage_quit": rage_quit_experiment,
        'withdrawal_queue_replacement_institutional': withdrawal_queue_replacement_institutional
    }

    if simulation_name not in simulations:
        logging.error(f"Simulation '{simulation_name}' not found.")
        return None, None

    create_experiment = simulations[simulation_name]
    experiment, simulation_hashes = create_experiment()

    experiment.engine = Engine(backend=Backend.MULTIPROCESSING, processes=5, raise_exceptions=False, drop_substeps=True)

    simulations = experiment.get_simulations()

    if len(simulations) == 1:
        experiment.engine.backend = Backend.SINGLE_PROCESS
        experiment.engine.processes = 1

    logging.info(f"Running simulation {simulation_name}")
    start_time = time.time()
    experiment_duration = 0

    if len(simulations) != 0:
        logging.info("Executing experiment")
        experiment.run()

        experiment_duration = time.time() - start_time
        logging.info(f"Experiment complete in {experiment_duration} seconds")

    if len(simulation_hashes) != 0 and len(simulations) != 0:
        logging.info("Post-processing results")

        result = merge_simulation_results(simulation_hashes, simulation_name, out_path)
        save_combined_actors_simulation_result(simulation_hashes, simulation_name, out_path)
        save_postprocessing_result(result, simulation_name, out_path)

        post_processing_duration = time.time() - start_time - experiment_duration
        logging.info(f"Post-processing complete in {post_processing_duration} seconds")

    logging.info("Simulation execution finished")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a simulation")
    parser.add_argument("--simulation_name", type=str, help="Name of the simulation to run")
    args = parser.parse_args()

    run(args.simulation_name)

import argparse
import logging
import sys
import time

from experiments.batch import run_simulation_batches
from experiments.simulation_configuration import get_path
from experiments.templates.actors_labelling import create_experiment as actors_labelling
from experiments.templates.constant_veto_signalling_loop import create_experiment as constant_veto_signalling_loop
from experiments.templates.model_validation import create_experiment as model_validation_experiment
from experiments.templates.rage_quit_scenario import create_experiment as rage_quit_experiment
from experiments.templates.signalling_thresholds_sweep_under_proposal_with_attack import (
    create_experiment as signalling_thresholds_sweep_under_proposal_with_attack,
)
from experiments.templates.single_attack_sweep_first_threshold import (
    create_experiment as single_attack_sweep_first_threshold,
)
from experiments.templates.single_attack_sweep_second_threshold import (
    create_experiment as single_attack_sweep_second_threshold,
)
from experiments.templates.veto_signalling_loop import create_experiment as veto_signalling_loop
from experiments.templates.withdrawal_queue_replacement import create_experiment as withdrawal_queue_experiment
from experiments.templates.withdrawal_queue_replacement_institutional import (
    create_experiment as withdrawal_queue_replacement_institutional,
)
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


def run(
    simulation_name: str = None,
    post_processing: bool = False,
    time_profiling: bool = False,
    processes: int = None,
    batch_size: int = 100,
    template_override=None,
    skip_existing_batches: bool = False,
):
    out_path = get_path()

    if simulation_name is None:
        simulation_name = "model_validation"

    if template_override:
        template_func = template_override
    else:
        simulations = {
            "model_validation": model_validation_experiment,
            "withdrawal_queue_replacement": withdrawal_queue_experiment,
            "rage_quit": rage_quit_experiment,
            "withdrawal_queue_replacement_institutional": withdrawal_queue_replacement_institutional,
            "signalling_thresholds_sweep_under_proposal_with_attack": signalling_thresholds_sweep_under_proposal_with_attack,
            "single_attack_sweep_first_threshold": single_attack_sweep_first_threshold,
            "single_attack_sweep_second_threshold": single_attack_sweep_second_threshold,
            "veto_signalling_loop": veto_signalling_loop,
            "constant_veto_signalling_loop": constant_veto_signalling_loop,
            "actors_labelling": actors_labelling,
        }

        if simulation_name not in simulations:
            logging.error(f"Simulation '{simulation_name}' not found.")
            return None, None

        template_func = simulations[simulation_name]

    _, template_params = template_func(simulation_name, return_template=True)
    if template_params is None:
        logging.error(f"Could not get parameters for simulation '{simulation_name}'")
        return None, None

    logging.info(f"Running simulation {simulation_name}")
    start_time = time.time()
    experiment_duration = 0

    try:
        simulation_hashes = run_simulation_batches(
            **template_params,
            processes=processes,
            batch_size=batch_size,
            time_profiling=time_profiling,
            out_dir=out_path.joinpath(simulation_name),
            skip_existing_batches=skip_existing_batches,
        )

        experiment_duration = time.time() - start_time
        logging.info(f"Experiment complete in {experiment_duration} seconds")

        if simulation_hashes and post_processing:
            logging.info("Post-processing results")
            post_process_start = time.time()

            result = merge_simulation_results(simulation_hashes, simulation_name, out_path)
            save_combined_actors_simulation_result(simulation_hashes, simulation_name, out_path)
            save_postprocessing_result(result, simulation_name, out_path)

            post_processing_duration = time.time() - post_process_start
            logging.info(f"Post-processing complete in {post_processing_duration} seconds")

    except Exception as e:
        logging.error(f"Error during simulation execution: {e}")
        raise
    finally:
        total_duration = time.time() - start_time
        logging.info(f"Total execution time: {total_duration} seconds")

    logging.info("Simulation execution finished")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a simulation")
    parser.add_argument("--simulation_name", type=str, help="Name of the simulation to run", required=True)
    parser.add_argument("--post_processing", action="store_true", help="Enable post-processing result")
    parser.add_argument("--time_profiling", action="store_true", help="Profile time usage")
    parser.add_argument("--processes", type=int, help="Number of processes to run", required=False, default=None)

    args = parser.parse_args()

    run(args.simulation_name, args.post_processing, args.time_profiling, args.processes)

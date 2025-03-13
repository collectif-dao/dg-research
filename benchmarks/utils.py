import logging
import sys
import time


def run_benchmark(
    template_func,
    simulation_name: str,
    post_processing: bool = False,
    time_profiling: bool = False,
    batch_size: int = 100,
):
    """
    Generic benchmark runner that uses the existing run_batches logic

    Args:
        template_func: The template function to use (e.g., model_validation)
        simulation_name: Name for the benchmark simulation
        post_processing: Whether to run post-processing
        time_profiling: Whether to enable time profiling
        batch_size: Size of simulation batches
    """
    from experiments.run import run  # Import here to avoid circular imports

    logging.info(f"Starting benchmark for {simulation_name}")
    start_time = time.time()

    try:
        run(
            simulation_name=simulation_name,
            post_processing=post_processing,
            time_profiling=time_profiling,
            batch_size=batch_size,
            template_override=template_func,
            skip_existing_batches=True,
        )
    finally:
        total_duration = time.time() - start_time
        logging.info(f"Benchmark complete in {total_duration} seconds")


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

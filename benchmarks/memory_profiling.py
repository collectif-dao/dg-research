from benchmarks.utils import run_benchmark, setup_logging
from experiments.templates.model_validation import create_experiment


def main():
    setup_logging()
    run_benchmark(
        template_func=create_experiment,
        simulation_name="memory_profiling_benchmark",
        batch_size=100,
    )


if __name__ == "__main__":
    main()

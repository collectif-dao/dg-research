from radcad import Backend, Engine

from experiments.simulation_configuration import get_path
from experiments.templates.model_validation import create_experiment
from experiments.utils import (
    merge_simulation_results,
    save_combined_actors_simulation_result,
    save_postprocessing_result,
)

out_path = get_path()

simulation_name = "single_process_benchmark"

experiment, simulation_hashes = create_experiment(simulation_name)
experiment.engine = Engine(backend=Backend.SINGLE_PROCESS, raise_exceptions=False, drop_substeps=True)

simulations = experiment.get_simulations()

if len(simulations) != 0:
    result = experiment.run()

    result = merge_simulation_results(simulation_hashes, simulation_name, out_path)
    save_combined_actors_simulation_result(simulation_hashes, simulation_name, out_path)
    save_postprocessing_result(result, simulation_name, out_path)

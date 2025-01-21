from experiments.run import run

if __name__ == "__main__":
    run(simulation_name='withdrawal_queue_replacement', processes=7, batch_size=100, execute_simulations=True, save_files=True)
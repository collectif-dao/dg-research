# Define the default target
.PHONY: run_simulations
run_simulations: install model_validation withdrawal_queue_replacement rage_quit withdrawal_queue_replacement_institutional signalling_thresholds_sweep_under_proposal_with_attack veto_signalling_loop thresholds_sweep actors_labelling

# Define targets for each simulation
.PHONY: model_validation
model_validation:
	@echo "Running model_validation simulation"
	@./run_simulation.sh model_validation --execute --save_files

.PHONY: withdrawal_queue_replacement
withdrawal_queue_replacement:
	@echo "Running withdrawal_queue_replacement simulation"
	@./run_simulation.sh withdrawal_queue_replacement --execute --save_files

.PHONY: rage_quit
rage_quit:
	@echo "Running rage_quit simulation"
	@./run_simulation.sh rage_quit --execute --save_files

.PHONY: withdrawal_queue_replacement_institutional
withdrawal_queue_replacement_institutional:
	@echo "Running withdrawal_queue_replacement_institutional simulation"
	@./run_simulation.sh withdrawal_queue_replacement_institutional --execute --save_files

.PHONY: signalling_thresholds_sweep_under_proposal_with_attack
signalling_thresholds_sweep_under_proposal_with_attack:
	@echo "Running signalling_thresholds_sweep_under_proposal_with_attack simulation"
	@./run_simulation.sh signalling_thresholds_sweep_under_proposal_with_attack --execute --save_files

.PHONY: veto_signalling_loop
veto_signalling_loop:
	@echo "Running veto_signalling_loop simulation"
	@./run_simulation.sh veto_signalling_loop --execute --save_files

.PHONY: constant_veto_signalling_loop
constant_veto_signalling_loop:
	@echo "Running constant_veto_signalling_loop simulation"
	@./run_simulation.sh constant_veto_signalling_loop --execute --save_files

.PHONY: thresholds_sweep
thresholds_sweep:
	@echo "Running single_attack_sweep_second_threshold"
	@./run_simulation.sh single_attack_sweep_second_threshold --execute --save_files
	@echo "Running single_attack_sweep_first_threshold"
	@./run_simulation.sh single_attack_sweep_first_threshold --execute --save_files

.PHONY: actors_labelling
actors_labelling:
	@echo "Running actors_labelling simulation"
	@./run_simulation.sh actors_labelling --execute --save_files

.PHONY: rage_quit_loop
rage_quit:
	@echo "Running rage_quit_loop simulation"
	@./run_simulation.sh rage_quit_loop --execute --save_files

# Install dependencies from requirements.txt if not already installed
.PHONY: install
install:
	@if ! pip freeze | grep -q -f requirements.txt; then \
		echo "Installing dependencies"; \
		pip install -r requirements.txt; \
	else \
		echo "Dependencies already installed"; \
	fi

# Define the default target
.PHONY: run_simulations
run_simulations: install model_validation withdrawal_queue_replacement rage_quit withdrawal_queue_replacement_institutional

# Define targets for each simulation
.PHONY: model_validation
model_validation:
	@echo "Running model_validation simulation"
	@./run_simulation.sh model_validation

.PHONY: withdrawal_queue_replacement
withdrawal_queue_replacement:
	@echo "Running withdrawal_queue_replacement simulation"
	@./run_simulation.sh withdrawal_queue_replacement

.PHONY: rage_quit
rage_quit:
	@echo "Running rage_quit simulation"
	@./run_simulation.sh rage_quit

.PHONY: withdrawal_queue_replacement_institutional
withdrawal_queue_replacement_institutional:
	@echo "Running withdrawal_queue_replacement_institutional simulation"
	@./run_simulation.sh withdrawal_queue_replacement_institutional

.PHONY: signalling_thresholds_sweep_under_proposal_with_attack
signalling_thresholds_sweep_under_proposal_with_attack:
	@echo "Running signalling_thresholds_sweep_under_proposal_with_attack simulation"
	@./run_simulation.sh signalling_thresholds_sweep_under_proposal_with_attack

.PHONY: veto_signalling_loop
veto_signalling_loop:
	@echo "Running veto_signalling_loop simulation"
	@./run_simulation.sh veto_signalling_loop

.PHONY: thresholds_sweep
thresholds_sweep:
	@echo "Running thresholds_sweep_second1"
	@./run_simulation.sh single_attack_sweep_second_threshold1
	@echo "Running thresholds_sweep_second2"
	@./run_simulation.sh single_attack_sweep_second_threshold2
# 	@echo "Running thresholds_sweep_first1"
# 	@./run_simulation.sh single_attack_sweep_first_threshold1
# 	@echo "Running thresholds_sweep_first2"
# 	@./run_simulation.sh single_attack_sweep_first_threshold2
# 	@echo "Running thresholds_sweep_first3"
# 	@./run_simulation.sh single_attack_sweep_first_threshold3
# 	@echo "Running thresholds_sweep_first4"
# 	@./run_simulation.sh single_attack_sweep_first_threshold4

# Install dependencies from requirements.txt if not already installed
.PHONY: install
install:
	@if ! pip freeze | grep -q -f requirements.txt; then \
		echo "Installing dependencies"; \
		pip install -r requirements.txt; \
	else \
		echo "Dependencies already installed"; \
	fi

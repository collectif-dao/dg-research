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

# Install dependencies from requirements.txt if not already installed
.PHONY: install
install:
	@if ! pip freeze | grep -q -f requirements.txt; then \
		echo "Installing dependencies"; \
		pip install -r requirements.txt; \
	else \
		echo "Dependencies already installed"; \
	fi

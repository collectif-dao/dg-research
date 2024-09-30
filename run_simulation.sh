#!/bin/bash

# Check if the simulation name is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <simulation_name>"
  exit 1
fi

# Run the simulation with the provided name
python3 -m experiments.run --simulation_name "$1"
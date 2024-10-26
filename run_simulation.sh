#!/bin/bash

# Default value for post_processing
post_processing=false

# Function to display usage
usage() {
  echo "Usage: $0 <simulation_name> [--post_processing]"
  exit 1
}

# Check if the simulation name is provided
[[ -z "$1" ]] && usage

# Parse optional arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --post_processing) post_processing=true ;;
    *) [[ -z "$simulation_name" ]] && simulation_name=$1 || usage ;;
  esac
  shift
done

# Check if simulation_name is set
[[ -z "$simulation_name" ]] && usage

# Run the simulation with the provided name and post_processing flag
python3 -m cProfile -o 'cprofile' experiments.run --simulation_name "$simulation_name" --post_processing "$post_processing" --time_profiling True
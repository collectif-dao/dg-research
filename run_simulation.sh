#!/bin/bash

# Function to display usage
usage() {
  echo "Usage: $0 <simulation_name> [--post_processing] [--time_profiling]"
  exit 1
}

# Check if the simulation name is provided
[[ -z "$1" ]] && usage

# Parse optional arguments
simulation_name=""

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --post_processing) post_processing=true ;;
    --time_profiling) time_profiling=true ;;
    *) 
      [[ -z "$simulation_name" ]] && simulation_name=$1 || usage 
      ;;
  esac
  shift
done

# Check if simulation_name is set
[[ -z "$simulation_name" ]] && usage

# Run the simulation with the provided name and flags
python3 -m experiments.run --simulation_name "$simulation_name" \
  ${post_processing:+--post_processing} \
  ${time_profiling:+--time_profiling}

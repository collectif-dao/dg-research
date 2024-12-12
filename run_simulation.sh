#!/bin/bash

# Add strict error handling
set -euo pipefail

# Function to display usage
usage() {
  echo "Usage: $0 <simulation_name> [--post_processing] [--time_profiling] [--execute] [--processes <num>] [--save_files] [--batch_size <num>]"
  exit 1
}

# Initialize variables with default values
post_processing=""
time_profiling=""
execute=""
save_files=""
processes=""
batch_size=""
simulation_name=""

# Check if the simulation name is provided
[[ $# -eq 0 ]] && usage

# Parse optional arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --post_processing) post_processing=true ;;
    --time_profiling) time_profiling=true ;;
    --execute) execute=true ;;
    --save_files) save_files=true ;;
    --processes) 
      shift
      processes=$1 
      ;;
    --batch_size) 
      shift
      batch_size=$1 
      ;;
    *)
      [[ -z "$simulation_name" ]] && simulation_name=$1 || usage 
      ;;
  esac
  shift
done

# Check if simulation_name is set
[[ -z "$simulation_name" ]] && usage

# Add input validation for numeric parameters
if [[ -n "$processes" ]] && ! [[ "$processes" =~ ^[0-9]+$ ]]; then
    echo "Error: processes must be a positive number"
    exit 1
fi

if [[ -n "$batch_size" ]] && ! [[ "$batch_size" =~ ^[0-9]+$ ]]; then
    echo "Error: batch_size must be a positive number"
    exit 1
fi

# Run the simulation with the provided name and flags
python3 -m experiments.run --simulation_name "$simulation_name" \
  ${post_processing:+--post_processing} \
  ${time_profiling:+--time_profiling} \
  ${execute:+--execute} \
  ${processes:+--processes "$processes"} \
  ${save_files:+--save_files} \
  ${batch_size:+--batch_size "$batch_size"}
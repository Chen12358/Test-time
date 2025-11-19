#!/bin/bash

# --- 1. Get Arguments ---
# Arguments are passed from the sbatch command
# $1: INPUT_PATH (e.g., batch_results_round_1.json)
# $2: OUTPUT_PATH (e.g., merged_results_round_1.json)
# $3: N_VALUE (e.g., 10)

INPUT_PATH=$1
OUTPUT_PATH=$2
N_VALUE=$3

echo "--- Merge Job Started on $(hostname) ---"
echo "Input file: $INPUT_PATH"
echo "Output file: $OUTPUT_PATH"
echo "N value: $N_VALUE"

# --- 2. Set up Environment ---
# Make sure this path is correct for your environment
source ~/.bashrc
conda activate Deepseek3

# Go to the correct project directory
# Assuming merge_job.slurm is in projects/Test-time
# If not, use the full path: cd /path/to/projects/Test-time
cd projects/Test-time

# --- 3. Run the Python Script ---
echo "Running merge_dedup.py..."

python merge_dedup.py \
    --input $INPUT_PATH \
    --output $OUTPUT_PATH \
    --dedup \
    --n $N_VALUE \
    --incr

echo "--- Merge Job Finished ---"
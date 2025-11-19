#!/bin/bash
#SBATCH --job-name=mediumweight_looped
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=71:59:00
#SBATCH --partition=pli-c
#SBATCH --account=pli
#SBATCH --output=slurm_output/%x-%j.out
#SBATCH --mail-user=st3812@princeton.edu
#SBATCH --mail-type=FAIL

source ~/.bashrc

cd projects/Test-time

conda activate Deepseek3

# --- Configuration for the loop ---
# NUM_ROUNDS=8  # <-- Set the total number of rounds here
# PASS=16
# NUM_ROUNDS=2  # <-- Set the total number of rounds here
# PASS=64
# NUM_ROUNDS=1  # <-- Set the total number of rounds here
# PASS=128


NUM_ROUNDS=2  # <-- Set the total number of rounds here
PASS=16

# MODEL_NAME="Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80"
MODEL_NAME="Goedel-Prover-V2-32B-reformat_revision_v2_S80-merge80"

# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/test/remained_minif2f.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split1.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split2.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split3.jsonl"
INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split4.jsonl"

FILENAME=$(basename "$INITIAL_PROBLEM_PATH")

BASE_NAME=${FILENAME%.*}

RESULTS_DIR="results/${MODEL_NAME}_${BASE_NAME}_${PASS}_${NUM_ROUNDS}"
mkdir -p $RESULTS_DIR

# Initialize the problem path for the first round
CURRENT_PROBLEM_PATH=$INITIAL_PROBLEM_PATH

# --- Start the loop ---
for (( i=1; i<=$NUM_ROUNDS; i++ ))
do
    echo "--- Starting Round $i of $NUM_ROUNDS ---"

    # Define filenames for this round
    BATCH_OUTPUT="${RESULTS_DIR}/batch_results_round_${i}.json"
    BATCH_LOG="${RESULTS_DIR}/batch_results_round_${i}.log"
    MERGED_OUTPUT="${RESULTS_DIR}/merged_results_round_${i}.json"

    # Set the --use_facts flag conditionally
    # It will be empty for the first round (i=1)
    # It will be "--use_facts" for all subsequent rounds
    USE_FACTS_FLAG=""
    if [ $i -gt 1 ]; then
        USE_FACTS_FLAG="--use_facts"
    fi

    # 1. Run the main test script
    echo "Running test_mediumweight.py (Round $i)..."
    python test/test_mediumweight.py \
        $USE_FACTS_FLAG \
        --problem_path $CURRENT_PROBLEM_PATH \
        --output_path $BATCH_OUTPUT \
        --num_passes $PASS \
        --model_name $MODEL_NAME \
        > $BATCH_LOG 2>&1

    # 2. Run the merge script
    echo "Running merge.py (Round $i)..."
    python merge.py \
        --input $BATCH_OUTPUT \
        --output $MERGED_OUTPUT

    # 3. Set the output of this round as the input for the next round
    CURRENT_PROBLEM_PATH=$MERGED_OUTPUT
    
    echo "--- Finished Round $i ---"
done

echo "All $NUM_ROUNDS rounds completed."
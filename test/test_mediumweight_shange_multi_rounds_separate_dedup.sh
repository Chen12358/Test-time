#!/bin/bash

# --- 0. Initial Setup ---
source ~/.bashrc

cd projects/Test-time

conda activate Deepseek3

echo "--- Job Started on $(hostname) ---"

# --- 1. Set up Tunnel Variables ---
LOCAL_PORT=10101
REMOTE_HOST="tiger3.princeton.edu"
REMOTE_PORT=9876

echo "Setting up SSH tunnel: localhost:${LOCAL_PORT} -> ${REMOTE_HOST}:${REMOTE_PORT}"

# --- 2. Establish SSH Tunnel in Background ---
ssh -f -N -L ${LOCAL_PORT}:${REMOTE_HOST}:${REMOTE_PORT} ${REMOTE_HOST}

# Get the Process ID (PID) of the tunnel we just started
# (Using pgrep for a more robust PID capture)
SSH_PID=$(pgrep -f "ssh -f -N -L ${LOCAL_PORT}:${REMOTE_HOST}:${REMOTE_PORT} ${REMOTE_HOST}")
echo "Tunnel established with PID ${SSH_PID}"

# Give the tunnel a moment to connect
sleep 3

# --- 3. Set Environment Variable for Python ---
export LEAN_GATEWAY_URL="http://localhost:${LOCAL_PORT}"

echo "Gateway URL set to: ${LEAN_GATEWAY_URL}"
echo "--- Running Python Script ---"

# --- 4. Set Main Loop Variables ---
NUM_ROUNDS=4
# PASS=16
# PASS=64
PASS=256
N=10 # dedup to N lemmas

MODEL_NAME="Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split1.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split2.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split3.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split4.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/test/remained_minif2f.jsonl"
# ... (other commented paths) ...
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split3_remove1.jsonl"
INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_25problems_split1.jsonl"


FILENAME=$(basename "$INITIAL_PROBLEM_PATH")
BASE_NAME=${FILENAME%.*}

RESULTS_DIR="results/${MODEL_NAME}_${BASE_NAME}_${PASS}_${NUM_ROUNDS}_dedup_incr_${N}"
mkdir -p $RESULTS_DIR

CURRENT_PROBLEM_PATH=$INITIAL_PROBLEM_PATH

# --- 5. Start the loop ---
for (( i=1; i<=$NUM_ROUNDS; i++ ))
do
    echo "--- Starting Round $i of $NUM_ROUNDS ---"

    # Define filenames for this round
    BATCH_OUTPUT="${RESULTS_DIR}/batch_results_round_${i}.json"
    BATCH_LOG="${RESULTS_DIR}/batch_results_round_${i}.log"
    MERGED_OUTPUT="${RESULTS_DIR}/merged_results_round_${i}.json"

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

    # 2. Submit the merge script as a separate GPU job and wait
    echo "Submitting merge_job.slurm (Round $i) as a GPU job..."
    
    MERGE_JOB_LOG="${RESULTS_DIR}/merge_job_round_${i}.slurm.log"
    
    # *** MODIFIED SECTION ***
    # Instead of the here-doc, we call the .slurm file directly
    # and pass the variables as arguments at the end.
    sbatch --wait \
           --job-name="merge_r${i}_${BASE_NAME}" \
           --gpus=1                  \
           --time=0:30:00            \
           --mem=128G                 \
           --partition=pli-c   \
           --account=pli      \
           --qos=pli-cp             \
           --output=$MERGE_JOB_LOG \
           merge_job.sh $BATCH_OUTPUT $MERGED_OUTPUT $N
    # *** END OF MODIFIED SECTION ***

    # --- Error Checking ---
    if [ $? -ne 0 ]; then
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "Error: sbatch job for merge_job.slurm (Round $i) failed."
        echo "Check the log for details: $MERGE_JOB_LOG"
        echo "Aborting the rest of the rounds."
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        
        break
    fi
    
    echo "Merge job for Round $i completed successfully."

    # 3. Set the output of this round as the input for the next round
    CURRENT_PROBLEM_PATH=$MERGED_OUTPUT
    
    echo "--- Finished Round $i ---"
done

echo "All $NUM_ROUNDS rounds completed or script aborted."

# --- 6. Cleanup ---
echo "Cleaning up tunnel (killing PID ${SSH_PID})..."
# Check if SSH_PID is not empty before trying to kill
if [ -n "$SSH_PID" ]; then
    kill $SSH_PID
else
    echo "Warning: Could not find SSH tunnel PID to kill."
fi

echo "--- Job Complete ---"
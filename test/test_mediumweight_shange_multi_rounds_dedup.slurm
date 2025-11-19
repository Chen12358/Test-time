#!/bin/bash
#SBATCH --job-name=vllm_worker-qwen3-v2-della9
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --mem=256G
#SBATCH --gres=gpu:1
#SBATCH --time=23:59:00
#SBATCH --partition=pli-c
#SBATCH --account=pli
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=st3812@princeton.edu
#SBATCH --output=slurm_output/%x-%j.out

# --- !! ADD THIS !! ---
# Exit immediately if a command fails
set -e
# ---

source ~/.bashrc

cd projects/Test-time

conda activate Deepseek3

echo "--- Job Started on $(hostname) ---"

# --- 1. Set up Tunnel Variables ---
# The local port we will use on this Della node
# (We used 12345 successfully in our test)
LOCAL_PORT=12345

# The gateway service on Tiger3
REMOTE_HOST="tiger3.princeton.edu"
REMOTE_PORT=9876

# DELLA_LOGIN_HOST="della.princeton.edu"
DELLA_LOGIN_HOST="della9"


# # !! CORRECTED KEY PATH !!
# KEY_PATH="/home/st3812/.ssh/id_ed25519"
# !! USE THE CORRECT KEY NAME !!
KEY_PATH="/home/st3812/.ssh/id_rsa"


# !! Define a path for the SSH control socket
CONTROL_SOCKET="/tmp/ssh-mux-$(whoami)-${REMOTE_HOST}"

echo "Setting up SSH tunnel: localhost:${LOCAL_PORT} -> ${DELLA_LOGIN_HOST} -> ${REMOTE_HOST}:${REMOTE_PORT}"
echo "Using key: ${KEY_PATH}"
echo "Control Socket: ${CONTROL_SOCKET}"

# --- 2. Establish SSH Tunnel in Background ---
#
# NEW COMMAND with:
# -M, -S, -o ControlPersist : For connection multiplexing (the concurrency fix)
# -o ServerAliveInterval=60  : For keep-alive (the timeout fix)
#
ssh -f -N \
    -i ${KEY_PATH} \
    -o StrictHostKeyChecking=no \
    -M -S ${CONTROL_SOCKET} \
    -o ControlPersist=10m \
    -o ServerAliveInterval=60 \
    -J ${DELLA_LOGIN_HOST} \
    -L ${LOCAL_PORT}:${REMOTE_HOST}:${REMOTE_PORT} \
    ${REMOTE_HOST}

# Get the Process ID (PID) of the tunnel we just started
SSH_PID=$!
echo "Tunnel established with PID ${SSH_PID}"

# Give the tunnel a moment to connect
sleep 3

# --- 3. Set Environment Variable for Python ---
# This assumes your Python script is modified to use this variable.
# Example: os.environ.get("GATEWAY_URL", "default_url")
export LEAN_GATEWAY_URL="http://localhost:${LOCAL_PORT}"

echo "Gateway URL set to: ${LEAN_GATEWAY_URL}"
echo "--- Running Python Script ---"

NUM_ROUNDS=7  # <-- Set the total number of rounds here
PASS=64
N=10 # dedup to N lemmas

# MODEL_NAME="Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80"
MODEL_NAME="Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80"

# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/test/remained_minif2f.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split1.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split2.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split3.jsonl"
INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split4.jsonl"

FILENAME=$(basename "$INITIAL_PROBLEM_PATH")

BASE_NAME=${FILENAME%.*}

RESULTS_DIR="results/${MODEL_NAME}_${BASE_NAME}_${PASS}_${NUM_ROUNDS}_dedup_incr_${N}"
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
    echo "Running merge_dedup.py (Round $i)..."
    python merge_dedup.py \
        --input $BATCH_OUTPUT \
        --output $MERGED_OUTPUT \
        --dedup \
        --n $N \
        --incr 

    

    # 3. Set the output of this round as the input for the next round
    CURRENT_PROBLEM_PATH=$MERGED_OUTPUT
    
    echo "--- Finished Round $i ---"
done

echo "All $NUM_ROUNDS rounds completed."


echo "Cleaning up tunnel (killing PID ${SSH_PID})..."
kill $SSH_PID

echo "--- Job Complete ---"
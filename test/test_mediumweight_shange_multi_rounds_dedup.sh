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

echo "Setting up SSH tunnel: localhost:${LOCAL_PORT} -> ${REMOTE_HOST}:${REMOTE_PORT}"

# --- 2. Establish SSH Tunnel in Background ---
# -f : Go into the background
# -N : Do not execute a remote command (just forward)
# -L : Define the [LOCAL_PORT]:[REMOTE_HOST]:[REMOTE_PORT] forwarding
ssh -f -N -L ${LOCAL_PORT}:${REMOTE_HOST}:${REMOTE_PORT} ${REMOTE_HOST}

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

NUM_ROUNDS=8  # <-- Set the total number of rounds here
PASS=16
N=10 # dedup to N lemmas

# MODEL_NAME="Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80"
MODEL_NAME="Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80"

INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/test/remained_minif2f.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split1.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split2.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split3.jsonl"
# INITIAL_PROBLEM_PATH="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/remained_minif2f_split4.jsonl"

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
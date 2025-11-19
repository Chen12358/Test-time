#!/bin/bash
#SBATCH --job-name=della-to-tiger    # Name of the job
#SBATCH --nodes=1                    # Run on a single node
#SBATCH --ntasks=1                   # Run a single task
#SBATCH --time=00:10:00              # 10-minute time limit
#SBATCH --mem=4G                     # 4GB of memory
#SBATCH --output=gateway_test.log    # Log file name

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

# --- 4. Run Your Python Command ---
# Your script will now connect to http://localhost:12345
# which the tunnel forwards to http://tiger3:9876
# python -m test.test_schedule_service

# python -m test.test_lightweight_v2_S80_merge80_axiom_misleading --use_lemma > lightweight_v2_S80_merge80_axiom_misleading_output.log 2>&1

# python -m test.test_lightweight_v2_S80_merge80_axiom_misleading \
#  --use_lemma \
#  --putnam_problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading_COMBINED.jsonl \
#  > lightweight_v2_S80_merge80_axiom_drop_09_misleading_COMBINED_pass32.log 2>&1


# python -m test.test_lightweight_v2_S80_merge80_axiom_misleading \
#  --use_lemma \
#  --putnam_problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_misleading_COMBINED.jsonl \
#  > lightweight_v2_S80_merge80_axiom_misleading_COMBINED_pass32.log 2>&1

# python -m test.test_lightweight_v2_S80_merge80_axiom_misleading \
#  --use_lemma \
#  --putnam_problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve.jsonl \
#  > lightweight_v2_S80_merge80_axiom_pass32.log 2>&1

## ====== ###
# python -m test.test_lightweight_v2_S80_merge80_axiom_misleading \
#  --use_lemma \
#  --putnam_problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_misleading_sampled_5.jsonl \
#  > lightweight_v2_S80_merge80_axiom_misleading_sampled_5_pass32.log 2>&1


# python -m test.test_lightweight_v2_S80_merge80_axiom_misleading \
#  --use_lemma \
#  --putnam_problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_misleading_sampled_10.jsonl \
#  > lightweight_v2_S80_merge80_axiom_misleading_sampled_10_pass32.log 2>&1


# python -m test.test_lightweight_v2_S80_merge80_axiom_misleading \
#  --use_lemma \
#  --putnam_problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_misleading_sampled_20.jsonl \
#  > lightweight_v2_S80_merge80_axiom_misleading_sampled_20_pass32.log 2>&1


# python -m test.test_lightweight_v2_S80_merge80_axiom_misleading \
#  --use_lemma \
#  --putnam_problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_misleading_sampled_30.jsonl \
#  > lightweight_v2_S80_merge80_axiom_misleading_sampled_30_pass32.log 2>&1

python -m test.test_lightweight_v2_S80_merge80_axiom_misleading \
 --use_lemma \
 --putnam_problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09.jsonl \
 > lightweight_v2_S80_merge80_axiom_drop_09_pass32.log 2>&1


python -m test.test_lightweight_v2_S80_merge80_axiom_misleading \
 --use_lemma \
 --putnam_problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading_sampled_5.jsonl \
 > lightweight_v2_S80_merge80_axiom_drop_09_misleading_sampled_5_pass32.log 2>&1


python -m test.test_lightweight_v2_S80_merge80_axiom_misleading \
 --use_lemma \
 --putnam_problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading_sampled_10.jsonl \
 > lightweight_v2_S80_merge80_axiom_drop_09_misleading_sampled_10_pass32.log 2>&1


python -m test.test_lightweight_v2_S80_merge80_axiom_misleading \
 --use_lemma \
 --putnam_problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading_sampled_20.jsonl \
 > lightweight_v2_S80_merge80_axiom_drop_09_misleading_sampled_20_pass32.log 2>&1


python -m test.test_lightweight_v2_S80_merge80_axiom_misleading \
 --use_lemma \
 --putnam_problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading_sampled_30.jsonl \
 > lightweight_v2_S80_merge80_axiom_drop_09_misleading_sampled_30_pass32.log 2>&1

echo "--- Python Script Finished ---"

# --- 5. Clean Up ---
echo "Cleaning up tunnel (killing PID ${SSH_PID})..."
kill $SSH_PID

echo "--- Job Complete ---"
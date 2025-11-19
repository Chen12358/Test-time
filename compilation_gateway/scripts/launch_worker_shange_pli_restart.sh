#!/bin/bash
#SBATCH --job-name=lean_worker
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=240G
#SBATCH --time=23:59:00
#SBATCH --account=pli
#SBATCH --partition=pli-c
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=st3812@princeton.edu
#SBATCH --output=slurm_output/%x-%j.out

# --- IMPORTANT: CONFIGURE THESE VARIABLES ---

source /scratch/gpfs/CHIJ/st3812/.bashrc

# source /scratch/gpfs/st3812/.bashrc

cd /scratch/gpfs/CHIJ/st3812/projects/Test-time

# The address of the node where you are running the compilation_gateway.py
# export GATEWAY_URL="http://della9.princeton.edu:9876"
export GATEWAY_URL="http://della-gpu.princeton.edu:9876"

# The absolute path to your mathlib4 project
# export LEAN_WORKSPACE="/scratch/gpfs/haoyu/goedel_informal/mathlib4"
# export LEAN_WORKSPACE="/scratch/gpfs/st3812/aiformath/Deepseek/mathlib4"
export LEAN_WORKSPACE="/scratch/gpfs/CHIJ/st3812/projects/Deepseek/mathlib4"

# --- Static Worker Configuration ---
NODE_IP=$(hostname -i)

# --- NEW: SET YOUR DESIRED LIFETIME ---
# Set the time in seconds you want each worker to live before restarting.
# 3600 seconds = 1 hour
# 1800 seconds = 30 minutes
# WORKER_LIFETIME_SECONDS=3600
WORKER_LIFETIME_SECONDS=3600

# --- Activate Environment & Enter Directory (Run Once) ---
cd compilation_gateway
# source /scratch/gpfs/haoyu/miniconda3/etc/profile.d/conda.sh
# conda activate goedelsdk
conda activate Deepseek3

echo "--- Starting Worker Loop (Restarting every ${WORKER_LIFETIME_SECONDS}s) ---"
echo "Job running on node: ${NODE_IP}"
echo "Gateway URL: ${GATEWAY_URL}"
echo "----------------------------------------"

# --- NEW: Main Worker Loop ---
while true
do
    # 1. Find a *new* free port for this run
    WORKER_PORT=$(python -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()')
    export WORKER_URL="http://${NODE_IP}:${WORKER_PORT}"

    echo "STARTING WORKER (PID: $$)"
    echo "Worker URL: ${WORKER_URL}"
    echo "Will run for ${WORKER_LIFETIME_SECONDS} seconds."
    
    # 2. Run uvicorn with a timeout.
    # The 'timeout' command sends a SIGTERM signal after the duration.
    # 'uvicorn' catches SIGTERM and triggers your @app.on_event("shutdown")
    # for a graceful shutdown of the pool.
    timeout ${WORKER_LIFETIME_SECONDS} uvicorn compilation_worker:app --host 0.0.0.0 --port ${WORKER_PORT}

    echo "----------------------------------------"
    echo "WORKER shut down (exit code $?). Restarting in 5 seconds..."
    echo "----------------------------------------"
    
    # 3. Short pause to let the socket close properly
    sleep 5
done
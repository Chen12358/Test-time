#!/bin/bash
#SBATCH --job-name=lean_worker
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=192G
#SBATCH --time=23:59:00
#SBATCH --account=chij
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=st3812@princeton.edu
#SBATCH --output=slurm_output/%x-%j.out

# --- IMPORTANT: CONFIGURE THESE VARIABLES ---
# The address of the node where you are running the compilation_gateway.py
export GATEWAY_URL="http://della9.princeton.edu:9876"
# The absolute path to your mathlib4 project
# export LEAN_WORKSPACE="/scratch/gpfs/haoyu/goedel_informal/mathlib4"

export LEAN_WORKSPACE="/scratch/gpfs/st3812/aiformath/Deepseek/mathlib4"

# --- Dynamic Worker Configuration ---
NODE_IP=$(hostname -i)

WORKER_PORT=$(python -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()')
echo "Found and assigned free port: ${WORKER_PORT}"

export WORKER_URL="http://${NODE_IP}:${WORKER_PORT}"

echo "--- Starting Lean Compilation Worker ---"
echo "Gateway URL: ${GATEWAY_URL}"
echo "Worker URL: ${WORKER_URL}"
echo "Local Processes: ${SLURM_CPUS_PER_TASK}"
echo "Lean Workspace: ${LEAN_WORKSPACE}"
echo "----------------------------------------"

cd compilation_gateway

# --- Activate Environment & Run ---
source /scratch/gpfs/haoyu/miniconda3/etc/profile.d/conda.sh
conda activate goedelsdk

uvicorn compilation_worker:app --host 0.0.0.0 --port ${WORKER_PORT}
#!/bin/bash
#SBATCH --job-name=vllm_worker
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=256G
#SBATCH --gres=gpu:2
#SBATCH --time=23:59:00
#SBATCH --partition=gpu-ee
#SBATCH --account=chij
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=sc7843@princeton.edu
#SBATCH --output=slurm_output/%x-%j.out

# --- User Configuration ---
# IMPORTANT: Set this to the address of your running gateway server.
export GATEWAY_URL="http://della9.princeton.edu:6666"

# Port for this vLLM worker. Ensure it's unique if running multiple workers on the same node.
# This command asks the OS for an available port and saves it to the variable.
WORKER_PORT=$(python -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()')
echo "Found and assigned free port: ${WORKER_PORT}"
# ---

# The Hugging Face model to be served by this worker.
MODEL_PATH="/scratch/gpfs/PLI/yong/gpt-oss-120b"
# NEW: The FRIENDLY NAME you will use to call the model via the API
FRIENDLY_MODEL_NAME="gpt-oss-120b"
TENSOR_PARALLEL_SIZE=2 # Should match --gpus-per-task

# --- Environment Setup ---

# Activate your Python/Conda environment where vLLM is installed.
# Replace with your specific environment activation command.
source /scratch/gpfs/st3812/packages/miniconda/etc/profile.d/conda.sh
conda activate /scratch/gpfs/st3812/packages/miniconda/envs/oss

echo "Environment activated."

# --- Launch vLLM Server ---
echo "Starting vLLM worker for model ${MODEL_NAME} on port ${WORKER_PORT}..."

export TIKTOKEN_ENCODINGS_BASE=/scratch/gpfs/yl7690/tiktoken_encodings

# Start the vLLM OpenAI-compatible API server in the background
python -m vllm.entrypoints.openai.api_server \
    --model "${MODEL_PATH}" \
    --host "0.0.0.0" \
    --port ${WORKER_PORT} \
    --tensor-parallel-size ${TENSOR_PARALLEL_SIZE} \
    --gpu-memory-utilization 0.8 \
    --trust-remote-code &

# Capture the Process ID (PID) of the backgrounded vLLM server
VLLM_PID=$!
echo "vLLM server started with PID: ${VLLM_PID}"

# --- Register Worker with Gateway ---
echo "Registering worker with gateway at ${GATEWAY_URL}..."
# NEW: Pass the friendly model name to the registration script
python register_worker.py \
    --gateway-url "${GATEWAY_URL}" \
    --port ${WORKER_PORT} \
    --model-name "${FRIENDLY_MODEL_NAME}" \
    --model-path "${MODEL_PATH}"

# --- Job Lifetime Management ---
# The 'wait' command is crucial. It pauses the script here, keeping the Slurm job
# alive until the vLLM server process (with PID $VLLM_PID) terminates.
# If you don't have this, the Slurm job will exit immediately after registration.
wait ${VLLM_PID}

echo "vLLM server process has terminated. Slurm job is now finishing."

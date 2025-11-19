#!/bin/bash
#SBATCH --job-name=vllm_worker_tool_1876
#SBATCH --output=slurm_output/%x-%j.out
#SBATCH --error=slurm_output/%x-%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --gres=gpu:2
#SBATCH --mem=200G
#SBATCH --time=23:59:00
#SBATCH --partition=pli-c
#SBATCH --account=pli
#SBATCH --mail-type=FAIL
#SBATCH --mail-user="jc1220@princeton.edu"


# --- User Configuration ---
# IMPORTANT: Set this to the address of your running gateway server.
# export GATEWAY_URL="http://della9.princeton.edu:1678"
export GATEWAY_URL="http://della9.princeton.edu:1876"

# Port for this vLLM worker. Ensure it's unique if running multiple workers on the same node.
# This command asks the OS for an available port and saves it to the variable.
WORKER_PORT=$(python -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()')
echo "Found and assigned free port: ${WORKER_PORT}"
# ---

# The Hugging Face model to be served by this worker (from start_vllm_tool.sh).
# Allow override via environment when invoked by a wrapper; otherwise, use default.
# MODEL_PATH="${MODEL_PATH:-/scratch/gpfs/CHIJ/juihui/merged_models/Qwen3-32B-RLv4-90-avg-0_70-merged_slerp_0_20}"

MODEL_PATH="/scratch/gpfs/CHIJ/juihui/models/Qwen3-32B"

FRIENDLY_MODEL_NAME="Qwen3-32B"


# MODEL_PATH="/scratch/gpfs/CHIJ/juihui/merged_models/Qwen3-32B-RLv4-90-avg-0_70-merged_slerp_0_10"

# FRIENDLY_MODEL_NAME="Qwen3-32B-RLv4-90-avg-0_70-merged_slerp_0_10"


# Match vLLM args from start_vllm_tool.sh
# Allow override via environment when invoked by a wrapper; otherwise, default to 2.
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-2}"
MAX_MODEL_LEN=32768
GPU_MEM_UTIL=0.9
TOOL_PARSER="hermes"

# --- Environment Setup ---
# Create a directory for logs if it doesn't exist
mkdir -p logs

# Activate your Python/Conda environment where vLLM is installed.
# Using the same env as the test launcher for consistency.
# source /scratch/gpfs/haoyu/miniconda3/etc/profile.d/conda.sh
# conda activate goedelsdk

# source /home/jc1220/.bashrc
# conda activate leansearch

source ~/.bashrc
cd /scratch/gpfs/CHIJ/st3812/projects/Test-time
conda activate Deepseek3

echo "Environment activated."

# --- Launch vLLM Server ---
echo "Starting vLLM worker for model ${MODEL_PATH} on port ${WORKER_PORT}..."

# Start the vLLM OpenAI-compatible API server in the background with tool-calling enabled
python -m vllm.entrypoints.openai.api_server \
    --model "${MODEL_PATH}" \
    --host "0.0.0.0" \
    --port ${WORKER_PORT} \
    --tensor-parallel-size ${TENSOR_PARALLEL_SIZE} \
    --max-model-len ${MAX_MODEL_LEN} \
    --gpu-memory-utilization ${GPU_MEM_UTIL} \
    --enable-auto-tool-choice \
    --tool-call-parser ${TOOL_PARSER} &

# Capture the Process ID (PID) of the backgrounded vLLM server
VLLM_PID=$!
echo "vLLM server started with PID: ${VLLM_PID}"

# Move into the inference_gateway module directory for registration
cd inference_gateway

# --- Register Worker with Gateway ---
echo "Registering worker with gateway at ${GATEWAY_URL}..."
python register_worker.py \
    --gateway-url "${GATEWAY_URL}" \
    --port ${WORKER_PORT} \
    --model-name "${FRIENDLY_MODEL_NAME}" \
    --model-path "${MODEL_PATH}"

# --- Job Lifetime Management ---
wait ${VLLM_PID}

echo "vLLM server process has terminated. Slurm job is now finishing."
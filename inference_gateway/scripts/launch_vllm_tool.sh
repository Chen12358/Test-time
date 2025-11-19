#!/bin/bash
#SBATCH --job-name=vllm_tool
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

# =============================================================================
# GPU CONFIGURATION (EDIT THIS SECTION)
# =============================================================================
# vLLM worker GPUs (e.g., "0,1,2,3" for 4 GPUs)
VLLM_GPUS="0,1"
# Number of GPUs for vLLM tensor parallelism (should match the count in VLLM_GPUS)
VLLM_TENSOR_PARALLEL_SIZE=2

# =============================================================================
# MODEL CONFIGURATION (EDIT THIS SECTION)
# =============================================================================
# The Hugging Face model to be served by the vLLM worker
MODEL_PATH="/scratch/gpfs/CHIJ/juihui/models/Qwen3-32B"
# MODEL_PATH="/scratch/gpfs/CHIJ/juihui/merged_models/Qwen3-32B-RLv4-90-avg-0_70-merged_slerp_0_80"
# MODEL_PATH="/scratch/gpfs/CHIJ/juihui/models/Qwen3-32B-RLv4-90-avg-0_70"

# The FRIENDLY NAME you will use to call the model via the API/gateway
FRIENDLY_MODEL_NAME="Qwen3-32B"
# FRIENDLY_MODEL_NAME="Qwen3-32B-RLv4-90-avg-0_70-merged_slerp_0_80"
# FRIENDLY_MODEL_NAME="Qwen3-32B-RLv4-90-avg-0_70"

# =============================================================================
# PATHS (DO NOT EDIT UNLESS NECESSARY)
# =============================================================================
BASE_DIR="/scratch/gpfs/jc1220/Test-time"


cd "${BASE_DIR}" || exit 1

VLLM_SCRIPT="${BASE_DIR}/inference_gateway/scripts/launch_worker_goedel_tool.sh"
LOG_DIR="${BASE_DIR}/logs"
SLURM_DIR="${BASE_DIR}/slurm_output"

mkdir -p "${LOG_DIR}" "${SLURM_DIR}"

echo "Node: $(hostname -f)"
echo "Starting combined job at: $(date)"
echo "vLLM GPUs: ${VLLM_GPUS} (Tensor Parallel: ${VLLM_TENSOR_PARALLEL_SIZE})"


# Start vLLM tool worker
if [[ ! -x "${VLLM_SCRIPT}" ]]; then
  chmod +x "${VLLM_SCRIPT}" || true
fi

echo "Launching vLLM tool worker (GPUs ${VLLM_GPUS}) using ${VLLM_SCRIPT}"
# Ensure relative paths inside the vLLM script (like `cd inference_gateway`) resolve correctly
pushd "${BASE_DIR}" >/dev/null
MODEL_PATH="${MODEL_PATH}" FRIENDLY_MODEL_NAME="${FRIENDLY_MODEL_NAME}" TENSOR_PARALLEL_SIZE="${VLLM_TENSOR_PARALLEL_SIZE}" \
  CUDA_VISIBLE_DEVICES="${VLLM_GPUS}" bash "${VLLM_SCRIPT}" \
  > "${LOG_DIR}/vllm_tool_worker_${SLURM_JOB_ID:-manual}.log" 2>&1 &
VLLM_WRAPPER_PID=$!
popd >/dev/null
echo "vLLM wrapper PID: ${VLLM_WRAPPER_PID}"

# Forward termination signals to child processes
cleanup() {
  echo "Caught signal, forwarding to children..."
  kill ${VLLM_WRAPPER_PID} 2>/dev/null || true
}
trap cleanup SIGINT SIGTERM

# Wait for vLLM
wait ${VLLM_WRAPPER_PID}

echo "vLLM worker has exited. Finished at: $(date)"
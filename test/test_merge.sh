#!/bin/bash
#SBATCH --job-name=vllm_worker
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --mem=120G
#SBATCH --gres=gpu:1
#SBATCH --time=0:59:00
#SBATCH --partition=pli-c
#SBATCH --mail-type=ALL
#SBATCH --mail-user=lyubh22@gmail.com
#SBATCH --output=slurm_output/%x-%j.out

source ~/.bashrc
conda activate vllm
cd /scratch/gpfs/yl7690/projects/Test-time

set -x

python merge_dedup.py --input mediumweight_batch_results_1030.json --output mediumweight_merged_results_1030_n_8_clever.json --dedup --n 8
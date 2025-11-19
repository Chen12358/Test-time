#!/bin/bash
#SBATCH --job-name=lightweigth
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=71:59:00
#SBATCH --partition=pli-c
#SBATCH --output=slurm_output/%x-%j.out

source ~/.bashrc

sleep 360

# python test/test_mediumweight.py --problem_path /scratch/gpfs/yl7690/projects/Test-time/test/minif2f_fixed.jsonl --output_path mediumweight_batch_results_32.json

# python merge.py

# python test/test_mediumweight.py --use_facts --output_path mediumweight_batch_results_325.json

python test/test_mediumweight.py --problem_path /scratch/gpfs/yl7690/projects/Test-time/remained_minif2f.jsonl --output_path mediumweight_batch_results_1030.json

python merge.py --input_paths mediumweight_batch_results_1030.json --output_path mediumweight_merged_results_1030.json

python test/test_mediumweight.py --use_facts --problem_path mediumweight_merged_results_1030.json --output_path mediumweight_final_results_1030.json
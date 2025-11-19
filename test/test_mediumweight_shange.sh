#!/bin/bash
#SBATCH --job-name=mediumweight
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=71:59:00
#SBATCH --partition=pli-c
#SBATCH --account=pli
#SBATCH --output=slurm_output/%x-%j.out
#SBATCH --mail-user=st3812@princeton.edu
#SBATCH --output=slurm_output/%x-%j.out
#SBATCH --mail-type=FAIL
source ~/.bashrc

cd projects/Test-time

conda activate Deepseek3

# sleep 360

# python test/test_mediumweight.py --problem_path /scratch/gpfs/yl7690/projects/Test-time/test/minif2f_fixed.jsonl --output_path mediumweight_batch_results_32.json

# python merge.py

# python test/test_mediumweight.py --use_facts --output_path mediumweight_batch_results_325.json

python test/test_mediumweight.py --problem_path /scratch/gpfs/CHIJ/st3812/projects/Test-time/test/remained_minif2f.jsonl --output_path mediumweight_batch_results_1101_shange.json > mediumweight_batch_results_1101_shange.log 2>&1

python merge.py --input mediumweight_batch_results_1101_shange.json --output mediumweight_merged_results_1101_shange.json

python test/test_mediumweight.py --use_facts --problem_path mediumweight_merged_results_1101_shange.json --output_path mediumweight_final_results_1101_shange.json > mediumweight_final_results_1101_shange.log 2>&1
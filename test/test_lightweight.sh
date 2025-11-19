#!/bin/bash
#SBATCH --job-name=lightweight
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=11:59:00
#SBATCH --partition=pli-c
#SBATCH --account=pli
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=st3812@princeton.edu
#SBATCH --output=slurm_output/%x-%j.out

source ~/.bashrc

python test/test_lightweight.py
#!/bin/bash
#SBATCH --job-name=eval_meld
#SBATCH --output=/scratch/data/bikash_rs/vivek/MELD-Data-Prep/logs/%x_%j.out
#SBATCH --error=/scratch/data/bikash_rs/vivek/MELD-Data-Prep/logs/%x_%j.err
#SBATCH --partition=dgx
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=1-00:00:00
#SBATCH --qos=fatqos
#SBATCH -D /scratch/data/bikash_rs/vivek/MELD-Data-Prep

# Create logs directory
mkdir -p logs

# Load CUDA module (adjust version based on your system)
# module load cuda/11.8

# Activate virtual environment
source meld-data-prep/bin/activate

python realigner/realigned_video_assembler_pyav.py
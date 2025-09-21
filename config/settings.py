"""
Configuration settings for the QML vs CML IDR prediction project.
"""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create directories if they don't exist
for directory in [DATA_DIR, RESULTS_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# Dataset configuration
PDBBIND_URL = "http://www.pdbbind.org.cn/download/PDBbind_v2020_refined.tar.gz"
PDBBIND_DIR = DATA_DIR / "pdbbind"
RUBISCO_PDB_IDS = ["8RUC", "1RCX", "1AAI", "3RBR", "1BXN", "1RBL", "1RBO"]

# IDR prediction parameters
DISORDER_THRESHOLD = 0.5
MIN_IDR_LENGTH = 10
MAX_IDR_LENGTH = 15
MAX_QUBITS_PER_RESIDUE = 4

# Quantum simulation parameters
QISKIT_BACKEND = "qasm_simulator"
SHOTS = 1024
NOISE_LEVELS = [0.0, 0.01, 0.05, 0.1]
ANSATZ_DEPTHS = [3, 5, 7]

# Classical ML parameters
ALPHAFOLD_MODELS = 5
ALPHAFOLD_RECYCLES = 3
ENERGY_MINIMIZATION_STEPS = 1000
ENERGY_TOLERANCE = 0.01  # kJ/mol

# Evaluation metrics
RMSD_THRESHOLD = 3.0  # Angstroms
RG_VARIANCE_THRESHOLD = 1.0  # Angstroms
ENERGY_CONVERGENCE_THRESHOLD = -100  # kcal/mol
TM_SCORE_THRESHOLD = 0.5
GDT_TS_THRESHOLD = 50.0

# Computational resources
MAX_MEMORY_GB = 16
GPU_MEMORY_GB = 8
PARALLEL_JOBS = 4

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Environment variables
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
os.environ.setdefault("OMP_NUM_THREADS", str(PARALLEL_JOBS))
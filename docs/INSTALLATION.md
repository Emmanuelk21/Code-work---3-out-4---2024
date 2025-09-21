# Installation Guide

This guide provides detailed instructions for setting up the QML-IDR pipeline on various systems.

## System Requirements

### Minimum Requirements
- **OS**: Linux (Ubuntu 20.04+), macOS (10.15+), Windows 10+
- **Python**: 3.10 or higher
- **RAM**: 8 GB minimum, 16 GB recommended
- **Storage**: 10 GB free space
- **CPU**: 4 cores minimum, 8 cores recommended

### Recommended Requirements
- **RAM**: 32 GB for large-scale analysis
- **GPU**: NVIDIA GPU with 8+ GB VRAM (for AlphaFold3)
- **Storage**: SSD with 50+ GB free space
- **CPU**: 16+ cores for parallel processing

## Installation Methods

### Method 1: Quick Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/qml-idr-rubisco.git
cd qml-idr-rubisco

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package and dependencies
pip install -e .

# Validate installation
qml-idr validate
```

### Method 2: Conda Environment

```bash
# Create conda environment
conda create -n qml-idr python=3.10
conda activate qml-idr

# Install conda packages
conda install -c conda-forge numpy pandas scipy matplotlib seaborn
conda install -c bioconda biopython mdtraj

# Install pip packages
pip install qiskit qiskit-aer qiskit-nature
pip install torch transformers
pip install snakemake click h5py

# Clone and install
git clone https://github.com/your-org/qml-idr-rubisco.git
cd qml-idr-rubisco
pip install -e .
```

### Method 3: Docker Installation

```bash
# Pull Docker image
docker pull your-org/qml-idr:latest

# Run container
docker run -it --rm -v $(pwd):/workspace your-org/qml-idr:latest

# Inside container
cd /workspace
qml-idr validate
```

## Detailed Component Installation

### 1. Quantum Computing Dependencies

```bash
# Core Qiskit packages
pip install qiskit>=1.0.0
pip install qiskit-aer>=0.13.0
pip install qiskit-nature>=0.7.0

# Optional: PennyLane for alternative quantum framework
pip install pennylane>=0.32.0
pip install pennylane-qiskit

# Verify quantum installation
python -c "import qiskit; print(qiskit.__version__)"
```

### 2. Bioinformatics Dependencies

```bash
# Core bioinformatics packages
pip install biopython>=1.81
pip install biotite>=0.39.0
pip install prody>=2.4.0

# Molecular dynamics and visualization
pip install mdtraj>=1.9.7
pip install nglview>=3.0.0

# Chemistry and drug discovery
pip install rdkit>=2023.3.1
pip install openmm>=8.0.0
pip install pdbfixer>=1.9

# Verify installation
python -c "from Bio import PDB; print('Biopython OK')"
```

### 3. Machine Learning Dependencies

```bash
# Core ML packages
pip install torch>=2.0.0
pip install transformers>=4.30.0
pip install scikit-learn>=1.3.0

# Optional: Additional ML frameworks
pip install tensorflow>=2.13.0  # If needed for custom models
pip install jax>=0.4.0          # For JAX-based implementations

# Verify installation
python -c "import torch; print(f'PyTorch {torch.__version__}')"
```

### 4. Data Processing Dependencies

```bash
# Data manipulation and analysis
pip install pandas>=2.0.0
pip install numpy>=1.24.0
pip install scipy>=1.10.0
pip install h5py>=3.8.0

# Visualization
pip install matplotlib>=3.6.0
pip install seaborn>=0.12.0
pip install plotly>=5.15.0

# Statistical analysis
pip install statsmodels>=0.14.0
pip install pingouin>=0.5.3
```

### 5. Workflow Management

```bash
# Snakemake for workflow automation
pip install snakemake>=7.30.0

# Additional workflow tools
pip install click>=8.1.0
pip install tqdm>=4.65.0
pip install joblib>=1.3.0

# Verify Snakemake
snakemake --version
```

## Platform-Specific Instructions

### Ubuntu/Debian Linux

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3.10 python3.10-venv python3.10-dev
sudo apt install -y build-essential cmake
sudo apt install -y libhdf5-dev libopenmpi-dev

# Install optional dependencies for visualization
sudo apt install -y ffmpeg  # For animations
sudo apt install -y pymol   # For structure visualization

# Continue with standard installation
python3.10 -m venv venv
source venv/bin/activate
pip install -e .
```

### CentOS/RHEL/Rocky Linux

```bash
# Enable EPEL repository
sudo dnf install -y epel-release

# Install system dependencies
sudo dnf install -y python3.10 python3.10-devel
sudo dnf install -y gcc gcc-c++ cmake
sudo dnf install -y hdf5-devel openmpi-devel

# Continue with standard installation
python3.10 -m venv venv
source venv/bin/activate
pip install -e .
```

### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python and dependencies
brew install python@3.10
brew install cmake hdf5 openmpi

# Optional: Install PyMOL
brew install pymol

# Continue with standard installation
python3.10 -m venv venv
source venv/bin/activate
pip install -e .
```

### Windows

#### Option 1: Windows Subsystem for Linux (WSL) - Recommended

```bash
# Install WSL2 with Ubuntu
wsl --install -d Ubuntu-20.04

# Inside WSL, follow Ubuntu instructions
sudo apt update && sudo apt upgrade -y
# ... continue with Ubuntu installation steps
```

#### Option 2: Native Windows

```powershell
# Install Python 3.10 from python.org
# Install Microsoft C++ Build Tools

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install Visual C++ redistributables if needed
# Continue with pip installation
pip install -e .
```

## GPU Setup (Optional)

### NVIDIA GPU for AlphaFold3

```bash
# Install NVIDIA drivers (system-specific)
# Ubuntu example:
sudo apt install -y nvidia-driver-525

# Install CUDA toolkit
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
sudo mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/12.2.0/local_installers/cuda-repo-ubuntu2004-12-2-local_12.2.0-535.54.03-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2004-12-2-local_12.2.0-535.54.03-1_amd64.deb
sudo cp /var/cuda-repo-ubuntu2004-12-2-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cuda

# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify GPU access
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

## AlphaFold3 Setup

**Note**: AlphaFold3 requires separate licensing from DeepMind.

```bash
# Download AlphaFold3 (requires registration)
# Visit: https://github.com/deepmind/alphafold3

# Download model parameters (large files ~2GB)
mkdir -p models/alphafold3
cd models/alphafold3

# Download databases (optional, for full MSA)
# This can require hundreds of GB
# wget https://ftp.ebi.ac.uk/pub/databases/alphafold/...

# Set environment variables
export ALPHAFOLD3_DATA_DIR=$(pwd)
echo 'export ALPHAFOLD3_DATA_DIR='$(pwd) >> ~/.bashrc
```

## Verification and Testing

### Basic Verification

```bash
# Check Python version
python --version  # Should be 3.10+

# Validate installation
qml-idr validate

# Check key imports
python -c "
import qiskit
import numpy as np
import pandas as pd
from Bio import PDB
import torch
print('All core packages imported successfully!')
"
```

### Run Test Suite

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-benchmark

# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run quick pipeline test
qml-idr test --fragments 2

# Run benchmarks
pytest tests/benchmarks/ --benchmark-only
```

### Performance Test

```bash
# Test quantum simulation performance
python -c "
from qiskit import QuantumCircuit, Aer
from qiskit.primitives import Estimator
import time

# Create test circuit
qc = QuantumCircuit(10)
for i in range(10):
    qc.h(i)
for i in range(9):
    qc.cx(i, i+1)

# Time simulation
start = time.time()
backend = Aer.get_backend('statevector_simulator')
job = backend.run(qc)
result = job.result()
end = time.time()

print(f'10-qubit simulation time: {end-start:.2f} seconds')
"
```

## Troubleshooting

### Common Issues

#### 1. Import Errors

```bash
# Error: ModuleNotFoundError: No module named 'qiskit'
# Solution: Ensure virtual environment is activated
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Reinstall if necessary
pip install --force-reinstall qiskit
```

#### 2. Memory Issues

```bash
# Error: Out of memory during quantum simulation
# Solution: Reduce number of qubits or use different backend

# In config/config.yaml:
quantum:
  simulator:
    max_qubits: 20  # Reduce from 30
    backend: "qasm_simulator"  # Use instead of statevector
```

#### 3. GPU Issues

```bash
# Error: CUDA out of memory
# Solution: Reduce batch size or use CPU

# Check GPU memory
nvidia-smi

# Use CPU fallback
export CUDA_VISIBLE_DEVICES=""
```

#### 4. Permission Issues (Linux/macOS)

```bash
# Error: Permission denied
# Solution: Fix permissions
sudo chown -R $USER:$USER ~/.local/
chmod -R 755 ~/.local/
```

### Getting Help

1. **Check logs**: Look in `logs/` directory for error messages
2. **Validate environment**: Run `qml-idr validate`
3. **Update packages**: `pip install --upgrade -r requirements.txt`
4. **Clean installation**: Remove `venv/` and reinstall
5. **GitHub Issues**: Report bugs at repository issues page

### Environment Variables

```bash
# Optional environment variables
export QML_IDR_DATA_DIR="/path/to/data"
export QML_IDR_RESULTS_DIR="/path/to/results"
export ALPHAFOLD3_DATA_DIR="/path/to/af3/data"
export CUDA_VISIBLE_DEVICES="0,1"  # GPU selection

# Add to ~/.bashrc for persistence
echo 'export QML_IDR_DATA_DIR="/path/to/data"' >> ~/.bashrc
```

## Next Steps

After successful installation:

1. **Configure the pipeline**: Edit `config/config.yaml`
2. **Run a test**: `qml-idr test --fragments 3`
3. **Read the tutorial**: See `docs/TUTORIAL.md`
4. **Run full pipeline**: `qml-idr run --max-fragments 20`

For additional help, see:
- [Tutorial](TUTORIAL.md)
- [Configuration Guide](CONFIGURATION.md)
- [API Reference](API.md)
- [FAQ](FAQ.md)
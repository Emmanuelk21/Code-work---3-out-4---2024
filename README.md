# Quantum vs Classical Machine Learning for RuBisCO IDR Prediction

This project implements a comprehensive comparative study between Quantum Machine Learning (QML) and Classical Machine Learning (CML) for predicting intrinsically disordered regions (IDRs) in the RuBisCO enzyme, with applications to sustainable carbon fixation engineering.

## Overview

The methodology focuses on:
- Leveraging the PDBbind dataset for benchmarking
- Hybrid quantum-classical workflows using free simulators
- Sustainability applications for RuBisCO engineering
- Reproducible, open-source implementation

## Project Structure

```
├── data/                    # Dataset storage and preprocessing
├── classical/              # Classical ML baseline (AlphaFold3)
├── quantum/                # QML framework (VQE-based)
├── evaluation/             # Metrics and comparative analysis
├── utils/                  # Utility functions and helpers
├── notebooks/              # Jupyter notebooks for analysis
├── config/                 # Configuration files
└── tests/                  # Unit tests
```

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Start

```python
from classical.alphafold_baseline import AlphaFoldPredictor
from quantum.vqe_framework import VQEPredictor
from evaluation.comparative_analysis import ComparativeAnalyzer

# Initialize predictors
classical_predictor = AlphaFoldPredictor()
quantum_predictor = VQEPredictor()

# Run comparative analysis
analyzer = ComparativeAnalyzer(classical_predictor, quantum_predictor)
results = analyzer.compare_idr_predictions(pdb_id="8RUC")
```

### Dataset Preparation

```python
from data.preprocessing import PDBbindProcessor

processor = PDBbindProcessor()
processor.download_pdbbind()
processor.extract_rubisco_structures()
processor.identify_idrs()
```

## Key Features

- **Hybrid QML Framework**: VQE-based approach for IDR conformational space exploration
- **Classical Baseline**: AlphaFold3 integration for comparison
- **Comprehensive Evaluation**: RMSD, radius of gyration, energy minimization metrics
- **Sustainability Focus**: Climate-resilient enzyme design applications
- **Reproducible**: Open-source tools and standardized workflows

## Citation

If you use this work, please cite the methodology paper and acknowledge the open-source tools used.

## License

MIT License - see LICENSE file for details.
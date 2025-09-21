# QML vs CML for RuBisCO IDR Prediction

A comprehensive comparison between Quantum Machine Learning (QML) and Classical Machine Learning (CML) approaches for predicting intrinsically disordered regions (IDRs) in the RuBisCO enzyme.

## Overview

This project implements a rigorous methodology for comparing quantum and classical machine learning approaches in the context of protein structure prediction, specifically focusing on intrinsically disordered regions (IDRs) in RuBisCO - a critical enzyme for carbon fixation and climate change mitigation.

### Key Features

- **Quantum ML Framework**: Variational Quantum Eigensolver (VQE) implementation for IDR conformational analysis
- **Classical ML Baseline**: AlphaFold3-based structure prediction with ensemble methods
- **Comprehensive Evaluation**: RMSD, energy minimization, statistical significance testing
- **Automated Workflow**: Snakemake pipeline for reproducible execution
- **Sustainability Focus**: Climate-resilient enzyme engineering applications

## Methodology

### Dataset Preparation
- **Source**: PDBbind database (refined subset, ~4,057 entries)
- **Target**: RuBisCO structures (8RUC, 1RCX, 1AAI, 3RBR)
- **IDR Detection**: IUPred3-based disorder prediction (threshold >0.5)
- **Fragment Size**: 10-15 residues (optimized for NISQ simulators)

### Quantum ML Approach (VQE)
- **Hamiltonian**: Ising-like model with pairwise interactions
- **Ansatz**: Hardware-efficient circuit (depth 3-5)
- **Optimizer**: COBYLA with 500 iterations
- **Noise Model**: Depolarizing channels (1-5% error rates)
- **Encoding**: Dihedral angle embedding via RY gates

### Classical ML Baseline (AlphaFold3)
- **Architecture**: Transformer-based multimer prediction
- **Configuration**: num_recycles=3, early_stop_tolerance=0.5
- **Ensemble**: 5 models per fragment for uncertainty quantification
- **Post-processing**: OpenMM energy minimization (Amber force field)

### Evaluation Metrics
- **Structural**: RMSD, GDT_TS, TM-score, radius of gyration
- **Energetic**: Potential energy, minimization success rate
- **Statistical**: Mann-Whitney U tests, chi-square analysis
- **Performance**: Runtime, convergence rate, memory usage

## Installation

### Requirements
- Python 3.10+
- 16 GB RAM (recommended)
- GPU (optional, for AlphaFold3)

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/qml-idr-rubisco.git
cd qml-idr-rubisco

# Install dependencies
pip install -r requirements.txt

# Install package
pip install -e .

# Validate installation
qml-idr validate

# Run quick test
qml-idr test --fragments 3
```

### Full Installation

```bash
# Create conda environment
conda create -n qml-idr python=3.10
conda activate qml-idr

# Install quantum computing packages
pip install qiskit qiskit-aer qiskit-nature

# Install bioinformatics packages
pip install biopython biotite mdtraj prody openmm

# Install ML packages
pip install torch transformers scikit-learn

# Install workflow management
pip install snakemake

# Install remaining dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

## Usage

### Command Line Interface

```bash
# Run complete pipeline
qml-idr run --max-fragments 20 --output-dir results

# Run only quantum ML
qml-idr run --qml-only --max-fragments 10

# Run only classical ML  
qml-idr run --cml-only --max-fragments 10

# Analyze existing results
qml-idr analyze results/complete_results.pkl --format markdown

# Clean temporary files
qml-idr clean
```

### Snakemake Workflow

```bash
# Run complete pipeline
snakemake --cores 4 --config max_fragments=20

# Run with custom configuration
snakemake --cores 8 --config max_fragments=50 output_dir=results_large

# Run test pipeline
snakemake test_pipeline --cores 2

# Generate visualizations only
snakemake generate_report --cores 1

# Clean all outputs
snakemake clean_all
```

### Python API

```python
from qml_idr.workflows.pipeline import IDRPredictionPipeline

# Initialize pipeline
pipeline = IDRPredictionPipeline(
    config_path="config/config.yaml",
    output_dir="results"
)

# Run complete comparison
results = pipeline.run_full_pipeline(max_fragments=20)

# Access results
qml_results = results['qml_results']
cml_results = results['cml_results']
comparison = results['comparison_results']

# Generate custom analysis
from qml_idr.evaluation.metrics import ComparativeAnalysis
analyzer = ComparativeAnalysis()
custom_comparison = analyzer.compare_methods(qml_results, cml_results)
```

## Configuration

The pipeline is configured via `config/config.yaml`:

```yaml
# Key configuration sections
data:
  pdbbind:
    version: "2020"
    refined_subset: true
  idr_settings:
    disorder_threshold: 0.5
    min_fragment_length: 10
    max_fragment_length: 15

quantum:
  simulator:
    backend: "aer_simulator"
    max_qubits: 30
  vqe:
    ansatz_depth: 3
    optimizer: "COBYLA"
    max_iterations: 500

classical:
  alphafold3:
    num_recycles: 3
    confidence_threshold: 50

evaluation:
  ensemble_size: 5
  metrics:
    rmsd_threshold: 3.0
    energy_threshold: -100
```

## Results and Analysis

### Expected Outputs

```
results/
├── qml_vs_cml_comparison_report.md    # Main comparison report
├── summary_statistics.json            # Quantitative metrics
├── complete_results.json             # Full pipeline results
├── executive_summary.md               # Executive summary
├── visualizations/                   # Plots and charts
│   ├── index.html                    # Interactive dashboard
│   └── *.png                         # Individual plots
└── models/                           # Saved models and states
```

### Key Metrics

The pipeline evaluates methods across multiple dimensions:

1. **Accuracy**: RMSD < 3Å target, TM-score > 0.5
2. **Reliability**: Convergence rate, ensemble consistency  
3. **Efficiency**: Runtime, memory usage, scalability
4. **Physical Validity**: Energy minimization, structural plausibility

### Statistical Analysis

- **Significance Testing**: p < 0.05 threshold
- **Effect Size**: Cohen's d for practical significance
- **Multiple Comparisons**: Bonferroni correction
- **Cross-Validation**: 80/20 train/test split

## Scientific Impact

### Applications

1. **Climate Engineering**: Enhanced CO₂ fixation efficiency
2. **Sustainable Agriculture**: Stress-resistant crop development  
3. **Quantum Biology**: Protein folding mechanism insights
4. **Drug Discovery**: IDR-targeting therapeutic strategies

### Publications

This methodology supports research in:
- Quantum machine learning for biology
- Protein disorder prediction
- Enzyme engineering for sustainability
- NISQ algorithm development

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone with development dependencies
git clone --recursive https://github.com/your-org/qml-idr-rubisco.git
cd qml-idr-rubisco

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/

# Run linting
flake8 src/
black src/
```

### Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests  
pytest tests/integration/

# Full pipeline test
qml-idr test --fragments 3

# Performance benchmarks
pytest tests/benchmarks/ --benchmark-only
```

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Citation

If you use this work in your research, please cite:

```bibtex
@software{qml_idr_rubisco_2025,
  title={QML vs CML for RuBisCO IDR Prediction: A Comparative Study},
  author={QML-IDR Research Team},
  year={2025},
  url={https://github.com/your-org/qml-idr-rubisco},
  version={1.0.0}
}
```

## Acknowledgments

- DeepMind for AlphaFold3 architecture insights
- IBM Qiskit team for quantum computing framework
- PDBbind consortium for structural data
- RCSB PDB for protein structure database

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/qml-idr-rubisco/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/qml-idr-rubisco/discussions)
- **Email**: qml-idr-support@your-org.com

---

**Disclaimer**: This is a research implementation. AlphaFold3 requires separate licensing from DeepMind. Quantum simulations are performed on classical hardware and may not reflect actual quantum device performance.
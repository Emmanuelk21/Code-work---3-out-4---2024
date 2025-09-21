# Tutorial: QML vs CML IDR Prediction

This tutorial walks through the complete process of comparing Quantum Machine Learning (QML) and Classical Machine Learning (CML) approaches for predicting intrinsically disordered regions (IDRs) in RuBisCO.

## Prerequisites

- Completed [installation](INSTALLATION.md)
- Basic understanding of protein structure
- Familiarity with command line interfaces
- Python programming knowledge (for advanced usage)

## Quick Start (5 minutes)

Let's start with a minimal example to verify everything works:

```bash
# Activate environment
source venv/bin/activate  # Linux/macOS
# or venv\Scripts\activate  # Windows

# Run quick test
qml-idr test --fragments 2

# Check results
ls results_test/
```

Expected output:
```
results_test/
├── qml_vs_cml_comparison_report.md
├── summary_statistics.json
├── complete_results.json
└── executive_summary.md
```

## Step-by-Step Tutorial

### Step 1: Configuration

First, let's examine and customize the configuration:

```bash
# View default configuration
cat config/config.yaml

# Copy to create custom configuration
cp config/config.yaml config/my_config.yaml
```

Edit key parameters in `config/my_config.yaml`:

```yaml
# Reduce for tutorial
data:
  idr_settings:
    max_fragment_length: 12  # Smaller for faster processing

quantum:
  simulator:
    max_qubits: 20          # Reduce for memory constraints
  vqe:
    max_iterations: 100     # Faster convergence

evaluation:
  ensemble_size: 3          # Smaller ensemble for speed
```

### Step 2: Understanding the Data

Let's explore what data the pipeline uses:

```bash
# Create a simple script to examine PDBbind data
cat > examine_data.py << 'EOF'
#!/usr/bin/env python3

import sys
sys.path.append('src')

from qml_idr.data.pdbbind_handler import PDBbindHandler
from qml_idr.data.idr_detector import IDRDetector

# Initialize handlers
pdbbind = PDBbindHandler()
idr_detector = IDRDetector()

# Process RuBisCO dataset
print("Processing RuBisCO dataset...")
rubisco_df = pdbbind.process_rubisco_dataset()
print(f"Found {len(rubisco_df)} RuBisCO structures")

if not rubisco_df.empty:
    print("\nStructure details:")
    print(rubisco_df[['pdb_code', 'chain_id', 'resolution', 'num_residues']].head())

    # Extract IDR fragments
    print("\nExtracting IDR fragments...")
    idr_df = idr_detector.process_rubisco_idrs(rubisco_df)
    print(f"Found {len(idr_df)} IDR fragments")
    
    if not idr_df.empty:
        print("\nIDR fragment details:")
        print(idr_df[['pdb_code', 'sequence', 'length', 'avg_disorder_score']].head())
EOF

python examine_data.py
```

### Step 3: Running Individual Components

#### 3A: Classical ML Only

```bash
# Run only AlphaFold3 predictions
qml-idr run --cml-only --max-fragments 5 --config config/my_config.yaml --output-dir results_cml

# Examine results
cat results_cml/summary_statistics.json | python -m json.tool
```

#### 3B: Quantum ML Only

```bash
# Run only VQE predictions
qml-idr run --qml-only --max-fragments 5 --config config/my_config.yaml --output-dir results_qml

# Examine quantum-specific results
python -c "
import pickle
with open('results_qml/qml_results.pkl', 'rb') as f:
    results = pickle.load(f)

for i, result in enumerate(results[:2]):
    print(f'Fragment {i+1}:')
    print(f'  Sequence: {result.get(\"sequence\", \"N/A\")[:20]}...')
    print(f'  Qubits used: {result.get(\"n_qubits_used\", \"N/A\")}')
    print(f'  Converged: {result.get(\"converged\", \"N/A\")}')
    print(f'  Runtime: {result.get(\"runtime\", 0):.2f}s')
    if 'ground_state_energy' in result:
        print(f'  Energy: {result[\"ground_state_energy\"]:.4f}')
    print()
"
```

### Step 4: Complete Comparison

Now let's run the full comparison:

```bash
# Run complete pipeline
qml-idr run --max-fragments 10 --config config/my_config.yaml --output-dir results_full --verbose

# This will take 15-30 minutes depending on your system
```

Monitor progress:
```bash
# In another terminal, watch the logs
tail -f logs/qml_idr.log
```

### Step 5: Analyzing Results

#### 5A: Quick Summary

```bash
# View executive summary
cat results_full/executive_summary.md
```

#### 5B: Detailed Analysis

```bash
# Generate additional analysis
qml-idr analyze results_full/complete_results.pkl --format markdown

# View detailed comparison report
less results_full/qml_vs_cml_comparison_report.md
```

#### 5C: Interactive Analysis

Create a Python script for custom analysis:

```python
#!/usr/bin/env python3
# analysis_script.py

import json
import pickle
import pandas as pd
import matplotlib.pyplot as plt

# Load results
with open('results_full/complete_results.json', 'r') as f:
    results = json.load(f)

# Extract method summaries
qml_summary = results['method_summaries']['qml']
cml_summary = results['method_summaries']['cml']

print("=== PERFORMANCE COMPARISON ===")
print(f"QML Success Rate: {qml_summary['success_rate']:.1%}")
print(f"CML Success Rate: {cml_summary['success_rate']:.1%}")
print(f"QML Mean Runtime: {qml_summary['mean_runtime']:.2f}s")
print(f"CML Mean Runtime: {cml_summary['mean_runtime']:.2f}s")

# Plot comparison
methods = ['QML', 'CML']
success_rates = [qml_summary['success_rate'], cml_summary['success_rate']]
runtimes = [qml_summary['mean_runtime'], cml_summary['mean_runtime']]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

# Success rate comparison
ax1.bar(methods, success_rates)
ax1.set_ylabel('Success Rate')
ax1.set_title('Prediction Success Rate')
ax1.set_ylim(0, 1)

# Runtime comparison
ax2.bar(methods, runtimes)
ax2.set_ylabel('Runtime (seconds)')
ax2.set_title('Mean Runtime per Fragment')

plt.tight_layout()
plt.savefig('results_full/performance_comparison.png', dpi=300)
plt.show()

print("\nPlot saved to results_full/performance_comparison.png")
```

Run the analysis:
```bash
python analysis_script.py
```

### Step 6: Using Snakemake Workflow

For more complex analyses, use the Snakemake workflow:

```bash
# View available rules
snakemake --list

# Run with custom parameters
snakemake --cores 4 --config max_fragments=15 output_dir=results_snake

# Run specific steps only
snakemake extract_idrs --cores 2
snakemake run_quantum_ml --cores 4

# Generate only visualizations
snakemake generate_report --cores 1
```

Monitor workflow:
```bash
# View workflow graph
snakemake --dag | dot -Tpng > workflow.png

# Dry run to see what would be executed
snakemake --dry-run --cores 4
```

### Step 7: Advanced Usage

#### 7A: Custom Quantum Circuits

Create a custom VQE ansatz:

```python
#!/usr/bin/env python3
# custom_quantum.py

import sys
sys.path.append('src')

from qml_idr.quantum.vqe_framework import VQEIDRSolver
import numpy as np

# Initialize solver with custom parameters
solver = VQEIDRSolver(
    n_qubits=12,
    ansatz_type='hardware_efficient'
)

# Create mock protein data
sequence = "MAKTLRKTLLGY"  # 12 amino acids
coordinates = np.random.random((12, 4, 3)) * 10  # Random coordinates

# Run prediction with custom stress conditions
stress_conditions = [
    {'perturbation_factor': 0.0, 'condition': 'normal'},
    {'perturbation_factor': 0.15, 'condition': 'extreme_stress'},
]

results = solver.run_ensemble_prediction(
    sequence, coordinates, n_runs=3, stress_conditions_list=stress_conditions
)

for i, result in enumerate(results):
    print(f"Run {i+1}: Energy = {result.get('ground_state_energy', 'N/A')}, "
          f"Converged = {result.get('converged', False)}")
```

#### 7B: Custom Evaluation Metrics

```python
#!/usr/bin/env python3
# custom_metrics.py

import sys
sys.path.append('src')

from qml_idr.evaluation.metrics import StructuralMetrics
import numpy as np

# Initialize metrics calculator
metrics = StructuralMetrics()

# Create mock structures for comparison
coords1 = np.random.random((10, 4, 3)) * 10
coords2 = coords1 + np.random.normal(0, 1, coords1.shape)  # Add noise

# Calculate custom metrics
rmsd = metrics.calculate_rmsd(coords1, coords2)
rg1 = metrics.calculate_radius_of_gyration(coords1)
rg2 = metrics.calculate_radius_of_gyration(coords2)

print(f"RMSD between structures: {rmsd:.3f} Å")
print(f"Radius of gyration 1: {rg1:.3f} Å")
print(f"Radius of gyration 2: {rg2:.3f} Å")
print(f"Rg difference: {abs(rg1 - rg2):.3f} Å")
```

### Step 8: Troubleshooting Common Issues

#### Issue 1: Memory Errors

```bash
# Reduce quantum system size
# Edit config/my_config.yaml:
quantum:
  simulator:
    max_qubits: 15          # Reduce from 20
  vqe:
    max_iterations: 50      # Reduce iterations

# Use fewer fragments
qml-idr run --max-fragments 3
```

#### Issue 2: Slow Performance

```bash
# Use parallel processing
export OMP_NUM_THREADS=4
snakemake --cores 8

# Reduce ensemble size
evaluation:
  ensemble_size: 2
```

#### Issue 3: AlphaFold3 Errors

```bash
# Check if mock mode is being used
grep "use_mock" logs/qml_idr.log

# The tutorial uses mock predictions by default
# For real AF3, you need to install it separately
```

### Step 9: Interpreting Results

#### Understanding the Comparison Report

The main report (`qml_vs_cml_comparison_report.md`) contains:

1. **Executive Summary**: Overall winner and key metrics
2. **QML Results**: Quantum-specific performance
3. **CML Results**: Classical method performance  
4. **Statistical Comparison**: Significance tests
5. **Performance by Metric**: Detailed breakdown

#### Key Metrics to Focus On

- **Success Rate**: Fraction of converged predictions
- **RMSD**: Structural accuracy (lower is better)
- **Runtime**: Computational efficiency
- **Energy**: Physical plausibility of structures

#### Making Scientific Conclusions

```python
# Example interpretation script
with open('results_full/summary_statistics.json', 'r') as f:
    stats = json.load(f)

qml_stats = stats['qml_summary']
cml_stats = stats['cml_summary']

print("=== SCIENTIFIC CONCLUSIONS ===")

# Success rate analysis
if qml_stats['success_rate'] > cml_stats['success_rate']:
    print("✓ QML shows higher reliability for IDR prediction")
else:
    print("✓ CML shows higher reliability for IDR prediction")

# Runtime analysis
qml_time = qml_stats['mean_runtime']
cml_time = cml_stats['mean_runtime']
speedup = max(qml_time, cml_time) / min(qml_time, cml_time)

if qml_time < cml_time:
    print(f"✓ QML is {speedup:.1f}x faster than CML")
else:
    print(f"✓ CML is {speedup:.1f}x faster than QML")

# Practical recommendations
if qml_stats['success_rate'] > 0.8 and qml_time < cml_time:
    print("→ Recommendation: Use QML for high-throughput IDR analysis")
elif cml_stats['success_rate'] > 0.9:
    print("→ Recommendation: Use CML for reliable structure prediction")
else:
    print("→ Recommendation: Use hybrid approach combining both methods")
```

## Next Steps

After completing this tutorial:

1. **Scale up**: Run with more fragments (`--max-fragments 50`)
2. **Customize**: Modify quantum circuits and classical models
3. **Extend**: Add new evaluation metrics or stress conditions
4. **Publish**: Use results for scientific publications
5. **Contribute**: Submit improvements to the project

## Additional Resources

- [API Documentation](API.md)
- [Configuration Guide](CONFIGURATION.md)
- [Methodology Details](METHODOLOGY.md)
- [FAQ](FAQ.md)
- [GitHub Issues](https://github.com/your-org/qml-idr-rubisco/issues)

## Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review log files in `logs/`
3. Run `qml-idr validate` to check installation
4. Search existing GitHub issues
5. Create a new issue with:
   - Your system information
   - Complete error messages
   - Steps to reproduce the problem

Happy analyzing! 🧬⚛️
# Methodology: QML vs CML for RuBisCO IDR Prediction

## Overview

This document provides a detailed description of the methodology used to compare Quantum Machine Learning (QML) and Classical Machine Learning (CML) approaches for predicting intrinsically disordered regions (IDRs) in the RuBisCO enzyme.

## Dataset Selection and Preprocessing

### PDBbind Database Selection

**Rationale**: The PDBbind database (version 2020) provides high-quality protein-ligand complexes with experimental 3D coordinates, binding affinities, and energy data. The refined subset contains approximately 4,057 non-redundant structures with resolution <2.5 Å.

**RuBisCO Structure Selection**:
- **8RUC**: Spinach RuBisCO large subunit with C-terminal IDR
- **1RCX**: Cyanobacterial RuBisCO
- **1AAI**: Tobacco RuBisCO  
- **3RBR**: Algal RuBisCO variant

**Selection Criteria**:
- Resolution ≤ 2.0 Å
- Complete protein chains
- Presence of IDR regions (>50 residues)
- Environmental relevance for climate applications

### IDR Detection and Fragmentation

**Disorder Prediction**: 
- Algorithm: Simplified IUPred3 implementation
- Threshold: Disorder score >0.5
- Window size: 7 residues for smoothing
- Validation: Against known IDR databases

**Fragment Extraction**:
- Length: 10-15 residues (optimized for NISQ constraints)
- Overlap: None (independent fragments)
- Quality filters: Complete backbone atoms, valid coordinates
- Total target: 50-100 fragments

**Preprocessing Steps**:
1. **Coordinate Extraction**: Backbone atoms (N, CA, C, O)
2. **Normalization**: Center of mass alignment
3. **Validation**: Stereochemical consistency
4. **Feature Encoding**: Multiple representations (angles, distances, properties)

## Classical Machine Learning Baseline

### AlphaFold3 Implementation

**Architecture**: Transformer-based structure prediction with attention mechanisms for protein-ligand interactions.

**Configuration Parameters**:
```yaml
alphafold3:
  num_ensemble: 1
  num_recycles: 3
  early_stop_tolerance: 0.5
  confidence_threshold: 50  # pLDDT
  max_template_date: "2024-01-01"
  model_preset: "monomer"
```

**Input Preparation**:
- **FASTA sequences**: IDR fragment sequences
- **MSA generation**: HHblits against UniRef90 (simplified for fragments)
- **Template search**: Against PDB70 database
- **Features**: Minimal feature set for computational efficiency

**Prediction Workflow**:
1. **Sequence encoding**: Amino acid to integer mapping
2. **MSA processing**: Evolutionary information extraction
3. **Structure prediction**: Transformer forward pass
4. **Confidence scoring**: pLDDT per-residue confidence
5. **Ensemble generation**: 5 models per fragment
6. **Post-processing**: OpenMM energy minimization

**Energy Minimization**:
- Force field: Amber ff14SB
- Solvent: Implicit (GBn2)
- Steps: 1000 steepest descent
- Convergence: 0.01 kJ/mol tolerance

### IDR-Specific Adaptations

**Challenge**: AlphaFold3 optimized for folded domains, struggles with disorder.

**Adaptations**:
- Reduced confidence threshold (50 vs 70)
- Extended recycling for flexibility
- Ensemble averaging for uncertainty quantification
- Post-hoc disorder scoring

## Quantum Machine Learning Framework

### Variational Quantum Eigensolver (VQE)

**Hamiltonian Construction**:
```
H = Σᵢ hᵢZᵢ + Σᵢⱼ JᵢⱼZᵢZⱼ
```

Where:
- `hᵢ`: Local field (amino acid hydrophobicity)
- `Jᵢⱼ`: Pairwise interaction (distance-dependent)
- `Zᵢ`: Pauli-Z operator on qubit i

**Interaction Model**:
- Cutoff distance: 5.0 Å
- Interaction strength: `J = -0.1 * exp(-r/3.0) * (hᵢ * hⱼ)`
- Stress perturbation: ±10% for environmental conditions

**Quantum Circuit Design**:

**Hardware-Efficient Ansatz**:
```
|ψ(θ)⟩ = ∏ₗ [∏ᵢ RY(θᵢˡ)RZ(φᵢˡ) ∏ᵢ CNOT(i,i+1)]|0⟩
```

Parameters:
- Depth: 3-5 layers
- Connectivity: Linear (nearest-neighbor)
- Gates: RY, RZ rotations + CNOT entanglers
- Total parameters: 2 × n_qubits × depth

**Optimization**:
- Algorithm: COBYLA (gradient-free)
- Iterations: 500 maximum
- Convergence: 10⁻⁴ Hartree tolerance
- Shots: 1024 per expectation value

### Noise Modeling

**NISQ Simulation**:
- Backend: Qiskit Aer simulator
- Noise model: Depolarizing channels
- Error rates: 1%, 3%, 5% (single-qubit gates)
- Two-qubit error: 2× single-qubit rate
- Readout error: Asymmetric (5-10%)

**Error Mitigation**:
- Zero-noise extrapolation
- Noise factors: [1.0, 1.5, 2.0]
- Richardson extrapolation to zero noise

### Quantum State Decoding

**Coordinate Reconstruction**:
1. Extract optimal parameters θ*
2. Map to dihedral angles: φ, ψ = f(θ*)
3. Generate backbone coordinates via geometry
4. Apply energy minimization for refinement

**Ensemble Generation**:
- Multiple VQE runs with different initializations
- Stress condition variations (temperature, pH, CO₂)
- Statistical ensemble of quantum states

## Comparative Evaluation

### Structural Metrics

**Root Mean Square Deviation (RMSD)**:
```
RMSD = √(1/N Σᵢ |rᵢᵖʳᵉᵈ - rᵢʳᵉᶠ|²)
```
- Atom type: Cα atoms
- Alignment: Optimal superposition
- Target: <3.0 Å for success

**Global Distance Test (GDT_TS)**:
```
GDT_TS = 1/4 Σ_cutoff P(cutoff)
```
- Cutoffs: 1, 2, 4, 8 Å
- Score range: 0-100%
- Target: >50% for good quality

**Template Modeling Score (TM-score)**:
```
TM-score = 1/L Σᵢ 1/(1+(dᵢ/d₀)²)
```
- Normalization: d₀ = 1.24∛(L-15) - 1.8
- Range: 0-1
- Target: >0.5 for correct fold

### Dynamic Properties

**Radius of Gyration**:
```
Rg = √(1/N Σᵢ |rᵢ - rcm|²)
```
- Measures compactness
- IDR-specific: Higher Rg expected
- Ensemble variance: <1.0 Å target

**End-to-End Distance**:
```
Ree = |r₁ - rₙ|
```
- Chain extension measure
- Correlation with disorder
- Ensemble distribution analysis

### Energy Evaluation

**Potential Energy Components**:
1. **Van der Waals**: Lennard-Jones 12-6 potential
2. **Electrostatic**: Coulomb interactions (distance-dependent dielectric)
3. **Solvation**: Generalized Born model
4. **Total**: Sum of all components

**Minimization Success**:
- Criterion: Final energy < -100 kcal/mol
- Convergence: Gradient norm < 0.01 kcal/mol/Å
- Success rate: Fraction meeting criteria

### Statistical Analysis

**Significance Testing**:
- Test: Mann-Whitney U (non-parametric)
- Null hypothesis: No difference between methods
- Significance level: p < 0.05
- Multiple comparisons: Bonferroni correction

**Effect Size**:
- Cohen's d for practical significance
- Small: d = 0.2, Medium: d = 0.5, Large: d = 0.8

**Cross-Validation**:
- Split: 80% training, 20% testing
- Stratification: By fragment length and disorder score
- Folds: 5-fold cross-validation for robust estimates

## Performance Benchmarking

### Computational Resources

**Classical ML (AlphaFold3)**:
- CPU: 16 cores, 64 GB RAM
- GPU: NVIDIA RTX 3060 (optional)
- Runtime: 5-10 minutes per fragment
- Memory: ~8 GB peak usage

**Quantum ML (VQE)**:
- CPU: 8 cores, 16 GB RAM  
- Simulator: Qiskit Aer (statevector/qasm)
- Runtime: 10-30 minutes per fragment
- Memory: Exponential scaling (2ⁿ qubits)

### Scalability Analysis

**Fragment Size Limits**:
- QML: 15 residues (30 qubits practical limit)
- CML: 100+ residues (memory permitting)
- Trade-off: Accuracy vs computational cost

**Parallelization**:
- Fragment-level: Embarrassingly parallel
- Ensemble-level: Independent runs
- Resource scaling: Linear with fragment count

## Validation and Quality Control

### Experimental Validation

**Reference Structures**:
- Crystal structures from PDB
- NMR ensembles for dynamic regions
- MD simulation trajectories (validation)

**Cross-Method Validation**:
- AlphaFold2 predictions as secondary reference
- Rosetta ab initio folding
- Consensus scoring across methods

### Error Analysis

**Sources of Uncertainty**:
1. **Quantum noise**: Decoherence, gate errors
2. **Classical approximations**: Force field limitations
3. **Sampling**: Finite ensemble size
4. **Model bias**: Training data limitations

**Uncertainty Quantification**:
- Bootstrap sampling for confidence intervals
- Ensemble variance as uncertainty measure
- Bayesian error propagation

## Sustainability and Environmental Impact

### Carbon Footprint

**Computational Energy**:
- Classical: ~0.5 kWh per fragment
- Quantum (simulated): ~1.0 kWh per fragment
- Comparison: Experimental structure determination ~1000 kWh

**Optimization**:
- Efficient algorithms to minimize runtime
- Green computing practices
- Renewable energy for computation

### Scientific Impact

**Climate Applications**:
- Enhanced CO₂ fixation efficiency
- Stress-resistant enzyme variants
- Agricultural sustainability improvements

**Methodological Advances**:
- Quantum algorithm development
- Protein disorder prediction
- Hybrid quantum-classical workflows

## Reproducibility and Open Science

### Code Availability

**Repository Structure**:
```
qml-idr-rubisco/
├── src/qml_idr/          # Core implementation
├── config/               # Configuration files
├── scripts/              # Workflow scripts
├── tests/                # Unit and integration tests
├── docs/                 # Documentation
└── results/              # Example outputs
```

**Version Control**:
- Git with semantic versioning
- Tagged releases for reproducibility
- Continuous integration testing

### Data Sharing

**Input Data**:
- PDB structure files (public)
- Processed IDR fragments (shared)
- Configuration parameters (documented)

**Output Data**:
- Prediction results (JSON/HDF5)
- Statistical analysis (CSV/Excel)
- Visualization plots (PNG/SVG)

### Documentation Standards

**Code Documentation**:
- Docstrings for all functions
- Type hints for clarity
- Usage examples in docstrings

**Methodology Documentation**:
- Detailed parameter justification
- Algorithm descriptions
- Validation procedures

This methodology provides a comprehensive framework for comparing quantum and classical approaches to IDR prediction, with applications in sustainable enzyme engineering and climate change mitigation.
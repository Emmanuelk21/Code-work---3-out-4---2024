# Contributing to QML-IDR RuBisCO

We welcome contributions to the QML vs CML IDR Prediction project! This guide outlines how to contribute effectively.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contribution Types](#contribution-types)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Review Process](#review-process)

## Getting Started

### Prerequisites

- Python 3.10+
- Git
- Basic understanding of quantum computing and protein structure
- Familiarity with scientific Python ecosystem

### First Steps

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/qml-idr-rubisco.git
   cd qml-idr-rubisco
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/original-org/qml-idr-rubisco.git
   ```

## Development Setup

### Environment Setup

```bash
# Create development environment
python -m venv venv-dev
source venv-dev/bin/activate  # Linux/macOS
# or venv-dev\Scripts\activate  # Windows

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Development Dependencies

The development setup includes additional packages:

```bash
# Testing
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-benchmark>=4.0.0
pytest-mock>=3.10.0

# Code quality
black>=23.0.0
flake8>=6.0.0
isort>=5.12.0
mypy>=1.0.0

# Documentation
sphinx>=6.0.0
sphinx-rtd-theme>=1.2.0
myst-parser>=1.0.0

# Pre-commit hooks
pre-commit>=3.0.0
```

### IDE Setup

#### VS Code
Recommended extensions:
- Python
- Pylance
- Black Formatter
- GitLens
- Jupyter

Settings (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./venv-dev/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.testing.pytestEnabled": true
}
```

#### PyCharm
- Configure interpreter to use `venv-dev`
- Enable Black formatter
- Configure pytest as test runner

## Contribution Types

### 1. Bug Reports

When reporting bugs, please include:

- **Environment**: OS, Python version, package versions
- **Steps to reproduce**: Minimal example
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Error messages**: Complete stack traces
- **Additional context**: Screenshots, logs, etc.

**Template**:
```markdown
## Bug Description
Brief description of the bug.

## Environment
- OS: Ubuntu 20.04
- Python: 3.10.8
- QML-IDR version: 1.0.0

## Steps to Reproduce
1. Run `qml-idr run --max-fragments 5`
2. ...

## Expected Behavior
The pipeline should complete successfully.

## Actual Behavior
The pipeline crashes with memory error.

## Error Message
```
[Complete error traceback here]
```

## Additional Context
- System has 8GB RAM
- Using default configuration
```

### 2. Feature Requests

For new features, please:

- **Check existing issues** to avoid duplicates
- **Describe the use case** and motivation
- **Propose an implementation** approach
- **Consider backwards compatibility**

### 3. Code Contributions

Areas where contributions are welcome:

#### Quantum ML Enhancements
- New quantum ansätze
- Error mitigation techniques
- Hybrid quantum-classical algorithms
- Noise model improvements

#### Classical ML Improvements
- Alternative structure prediction methods
- Ensemble techniques
- Post-processing algorithms
- Performance optimizations

#### Evaluation and Analysis
- New structural metrics
- Statistical analysis methods
- Visualization improvements
- Benchmarking tools

#### Infrastructure
- Workflow optimizations
- Documentation improvements
- Testing enhancements
- CI/CD improvements

## Development Workflow

### Branch Management

We use a Git flow-inspired workflow:

- `main`: Stable release branch
- `develop`: Integration branch for new features
- `feature/feature-name`: Feature development
- `bugfix/bug-description`: Bug fixes
- `hotfix/critical-fix`: Critical production fixes

### Creating a Feature

1. **Create feature branch**:
   ```bash
   git checkout develop
   git pull upstream develop
   git checkout -b feature/new-quantum-ansatz
   ```

2. **Make changes** following code standards

3. **Test thoroughly**:
   ```bash
   pytest tests/
   qml-idr test --fragments 2
   ```

4. **Commit changes**:
   ```bash
   git add .
   git commit -m "Add hardware-efficient ansatz with custom topology"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/new-quantum-ansatz
   # Create PR on GitHub
   ```

### Commit Message Guidelines

Follow conventional commit format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(quantum): add QAOA ansatz for protein folding

Implements the Quantum Approximate Optimization Algorithm (QAOA)
as an alternative to VQE for protein structure prediction.

Closes #123
```

```
fix(classical): resolve memory leak in AlphaFold3 ensemble

- Fix memory accumulation during ensemble prediction
- Add proper cleanup in AlphaFold3Baseline destructor
- Update documentation with memory requirements

Fixes #456
```

## Code Standards

### Python Style

We follow PEP 8 with some modifications:

```python
# Use Black formatter (line length: 88)
# Import organization with isort
# Type hints for all public functions
# Docstrings for all modules, classes, and functions

def predict_structure(sequence: str, n_models: int = 5) -> List[Path]:
    """Predict protein structure using ensemble method.
    
    Args:
        sequence: Protein sequence in single-letter code
        n_models: Number of models in ensemble
        
    Returns:
        List of paths to predicted structure files
        
    Raises:
        ValueError: If sequence contains invalid characters
        RuntimeError: If prediction fails
    """
    pass
```

### Code Quality Tools

All code must pass:

```bash
# Formatting
black src/ tests/
isort src/ tests/

# Linting
flake8 src/ tests/

# Type checking
mypy src/

# Tests
pytest tests/ --cov=src/
```

### Performance Guidelines

- **Profile before optimizing**: Use `cProfile` or `line_profiler`
- **Memory efficiency**: Monitor memory usage for large datasets
- **Parallel processing**: Use `multiprocessing` or `joblib` where appropriate
- **Caching**: Cache expensive computations with `functools.lru_cache`

### Scientific Computing Best Practices

- **Numerical stability**: Check for NaN/inf values
- **Reproducibility**: Set random seeds appropriately
- **Units**: Always specify and check physical units
- **Validation**: Compare against known results when possible

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                 # Unit tests
│   ├── test_data/
│   ├── test_quantum/
│   ├── test_classical/
│   └── test_evaluation/
├── integration/          # Integration tests
│   ├── test_pipeline/
│   └── test_workflows/
├── benchmarks/          # Performance benchmarks
└── fixtures/            # Test data and fixtures
```

### Writing Tests

#### Unit Tests
```python
import pytest
from qml_idr.quantum.vqe_framework import VQEIDRSolver

class TestVQEIDRSolver:
    """Test VQE solver functionality."""
    
    def test_initialization(self):
        """Test solver initialization with valid parameters."""
        solver = VQEIDRSolver(n_qubits=10)
        assert solver.n_qubits == 10
        assert solver.ansatz is not None
    
    def test_invalid_qubits(self):
        """Test error handling for invalid qubit count."""
        with pytest.raises(ValueError, match="n_qubits must be positive"):
            VQEIDRSolver(n_qubits=0)
    
    @pytest.mark.parametrize("n_qubits,expected_params", [
        (5, 30),   # 2 * 5 * 3 (depth=3)
        (10, 60),  # 2 * 10 * 3
    ])
    def test_parameter_count(self, n_qubits, expected_params):
        """Test parameter count for different system sizes."""
        solver = VQEIDRSolver(n_qubits=n_qubits)
        assert solver.ansatz.num_parameters == expected_params
```

#### Integration Tests
```python
def test_full_pipeline_small():
    """Test complete pipeline with minimal data."""
    pipeline = IDRPredictionPipeline(output_dir="test_output")
    results = pipeline.run_full_pipeline(max_fragments=2)
    
    assert 'qml_results' in results
    assert 'cml_results' in results
    assert len(results['qml_results']) > 0
    assert len(results['cml_results']) > 0
```

#### Benchmarks
```python
def test_vqe_performance(benchmark):
    """Benchmark VQE solver performance."""
    solver = VQEIDRSolver(n_qubits=12)
    sequence = "MAKTLRKTLLGY"
    coords = np.random.random((12, 4, 3)) * 10
    
    result = benchmark(solver.predict_structure, sequence, coords)
    assert result['converged']
```

### Test Data

Use fixtures for test data:

```python
@pytest.fixture
def sample_protein_data():
    """Provide sample protein data for testing."""
    return {
        'sequence': 'MAKTLRKTLLGY',
        'coordinates': np.random.random((12, 4, 3)) * 10,
        'pdb_code': 'TEST',
        'chain_id': 'A'
    }

def test_idr_detection(sample_protein_data):
    """Test IDR detection with sample data."""
    detector = IDRDetector()
    result = detector.predict_disorder_iupred(sample_protein_data['sequence'])
    assert len(result) == len(sample_protein_data['sequence'])
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_quantum/test_vqe_framework.py

# With coverage
pytest --cov=src/ --cov-report=html

# Benchmarks only
pytest tests/benchmarks/ --benchmark-only

# Integration tests (slow)
pytest tests/integration/ -v

# Parallel execution
pytest -n 4  # requires pytest-xdist
```

## Documentation

### Docstring Standards

Use Google-style docstrings:

```python
def calculate_rmsd(structure1: np.ndarray, structure2: np.ndarray) -> float:
    """Calculate root mean square deviation between structures.
    
    This function computes the RMSD after optimal superposition of the
    two input structures using the Kabsch algorithm.
    
    Args:
        structure1: First structure coordinates with shape (N, 3)
        structure2: Second structure coordinates with shape (N, 3)
        
    Returns:
        RMSD value in Angstroms
        
    Raises:
        ValueError: If structures have different shapes
        
    Example:
        >>> coords1 = np.random.random((10, 3))
        >>> coords2 = np.random.random((10, 3))
        >>> rmsd = calculate_rmsd(coords1, coords2)
        >>> print(f"RMSD: {rmsd:.3f} Å")
        
    Note:
        Structures are automatically centered before superposition.
        
    References:
        Kabsch, W. (1976). A solution for the best rotation to relate
        two sets of vectors. Acta Crystallographica, 32(5), 922-923.
    """
```

### API Documentation

Update API documentation when adding new functions:

```bash
# Generate API docs
cd docs/
sphinx-apidoc -o api/ ../src/qml_idr/
make html
```

### User Documentation

Update relevant documentation files:
- `README.md`: Overview and quick start
- `docs/TUTORIAL.md`: Step-by-step guide
- `docs/METHODOLOGY.md`: Scientific methodology
- `docs/API.md`: API reference

## Review Process

### Pull Request Guidelines

**PR Title**: Use conventional commit format
**PR Description**: Include:
- Summary of changes
- Motivation and context
- Testing performed
- Breaking changes (if any)
- Related issues

**Template**:
```markdown
## Description
Brief description of changes made.

## Motivation
Why is this change necessary? What problem does it solve?

## Changes Made
- [ ] Added new quantum ansatz
- [ ] Updated documentation
- [ ] Added tests

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Breaking Changes
None / List any breaking changes

## Related Issues
Closes #123
Related to #456
```

### Review Checklist

Reviewers will check:

- [ ] **Functionality**: Code works as intended
- [ ] **Tests**: Adequate test coverage (>80%)
- [ ] **Documentation**: Clear docstrings and comments
- [ ] **Style**: Follows project conventions
- [ ] **Performance**: No significant performance regressions
- [ ] **Compatibility**: Maintains backwards compatibility
- [ ] **Security**: No security vulnerabilities

### Review Process

1. **Automated checks**: CI/CD pipeline runs automatically
2. **Peer review**: At least one maintainer reviews
3. **Address feedback**: Author makes requested changes
4. **Final approval**: Maintainer approves and merges

### Merge Requirements

- All CI checks pass
- At least one approving review
- No requested changes
- Up-to-date with target branch

## Recognition

Contributors are recognized in:
- `CONTRIBUTORS.md` file
- GitHub contributors page
- Release notes for significant contributions
- Academic publications (for substantial scientific contributions)

## Code of Conduct

We follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/). Please read it before contributing.

### Summary

- **Be respectful**: Treat all community members with respect
- **Be inclusive**: Welcome newcomers and diverse perspectives
- **Be constructive**: Provide helpful feedback and suggestions
- **Be patient**: Remember that everyone is learning

## Getting Help

- **GitHub Discussions**: For general questions and ideas
- **GitHub Issues**: For bug reports and feature requests
- **Email**: maintainers@qml-idr-project.org
- **Documentation**: Check existing docs first

## Thank You!

Thank you for contributing to advancing quantum machine learning applications in computational biology! Your contributions help make sustainable enzyme engineering possible.

---

*This contributing guide is adapted from best practices in open-source scientific software development.*
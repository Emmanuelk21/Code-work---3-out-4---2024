# Contributing to Quantum vs Classical ML for RuBisCO IDR Prediction

Thank you for your interest in contributing to this project! This document provides guidelines for contributing.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/quantum-classical-idr-prediction.git
   cd quantum-classical-idr-prediction
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🔧 Development Setup

### Running Tests
```bash
python tests/test_basic_functionality.py
```

### Running the Analysis
```bash
python run_analysis.py
```

### Code Style
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and modular

## 📝 Types of Contributions

### 🐛 Bug Reports
- Use the GitHub issue tracker
- Provide clear reproduction steps
- Include system information (OS, Python version)
- Attach relevant error messages and logs

### ✨ Feature Requests
- Describe the feature clearly
- Explain the use case and benefits
- Consider implementation complexity
- Check for existing similar requests

### 🔬 Code Contributions
- Create feature branches from `main`
- Write tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 📚 Documentation
- Improve README files
- Add code comments and docstrings
- Create tutorials or examples
- Fix typos and improve clarity

## 🎯 Areas for Contribution

### High Priority
- [ ] Add support for larger IDR fragments (>15 residues)
- [ ] Implement real quantum hardware integration
- [ ] Add experimental validation with NMR/SAXS data
- [ ] Improve statistical analysis and significance testing

### Medium Priority
- [ ] Add more visualization options
- [ ] Implement additional quantum algorithms
- [ ] Add support for more protein types
- [ ] Create interactive Jupyter notebooks

### Low Priority
- [ ] Add GUI interface
- [ ] Implement parallel processing
- [ ] Add cloud deployment options
- [ ] Create Docker containers

## 🔄 Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write clean, well-documented code
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**:
   ```bash
   python run_analysis.py
   python tests/test_basic_functionality.py
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add: brief description of changes"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**:
   - Provide a clear title and description
   - Reference any related issues
   - Include screenshots for UI changes
   - Wait for review and feedback

## 📋 Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
- [ ] Tests pass locally
- [ ] Analysis runs successfully
- [ ] No new warnings or errors

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## 🏷️ Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `question`: Further information is requested

## 💬 Communication

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Pull Requests**: For code contributions and reviews

## 📜 Code of Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/) Code of Conduct.

## 🙏 Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Academic publications (where appropriate)

Thank you for contributing to quantum machine learning research!

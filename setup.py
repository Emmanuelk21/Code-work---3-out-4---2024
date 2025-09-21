from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="quantum-classical-idr-prediction",
    version="1.0.0",
    author="Quantum ML Research Team",
    author_email="research@example.com",
    description="Quantum vs Classical Machine Learning for RuBisCO IDR Prediction",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/quantum-classical-idr-prediction",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
        "pandas>=1.3.0",
        "matplotlib>=3.4.0",
        "seaborn>=0.11.0",
        "requests>=2.25.0",
        "biopython>=1.79",
        "qiskit>=0.45.0",
        "scipy>=1.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.9",
            "jupyter>=1.0.0",
        ],
        "viz": [
            "plotly>=5.0.0",
            "bokeh>=2.4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "run-idr-analysis=run_analysis:main",
        ],
    },
)

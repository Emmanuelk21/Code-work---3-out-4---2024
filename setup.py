from setuptools import setup, find_packages

setup(
    name="qml-idr-rubisco",
    version="1.0.0",
    description="Quantum vs Classical Machine Learning for RuBisCO IDR Prediction",
    author="QML-IDR Research Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        line.strip() 
        for line in open("requirements.txt").readlines() 
        if line.strip() and not line.startswith("#")
    ],
    entry_points={
        "console_scripts": [
            "qml-idr=qml_idr.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Physics",
    ],
)
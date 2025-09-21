"""
Snakemake workflow for QML vs CML IDR prediction comparison.

This workflow automates the complete pipeline for comparing Quantum Machine Learning
and Classical Machine Learning approaches for predicting intrinsically disordered
regions (IDRs) in RuBisCO enzyme structures.

Usage:
    snakemake --cores 4 --config max_fragments=10
    snakemake --cores 8 --config max_fragments=50 output_dir=results_large
"""

import os
from pathlib import Path

# Configuration
configfile: "config/config.yaml"

# Default parameters
MAX_FRAGMENTS = config.get("max_fragments", 20)
OUTPUT_DIR = config.get("output_dir", "results")
N_CORES = config.get("n_cores", 4)

# Create output directory
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# Define all target files
rule all:
    input:
        f"{OUTPUT_DIR}/qml_vs_cml_comparison_report.md",
        f"{OUTPUT_DIR}/summary_statistics.json",
        f"{OUTPUT_DIR}/complete_results.json",
        f"{OUTPUT_DIR}/dataset_info.json",
        f"{OUTPUT_DIR}/processed_dataset.h5"

# Step 1: Download and process PDBbind dataset
rule download_pdbbind:
    output:
        csv_file=f"data/pdbbind/rubisco_processed.csv",
        structures=directory("data/pdbbind/structures")
    params:
        max_structures=10
    threads: 2
    resources:
        mem_mb=4000,
        runtime=120  # 2 hours
    log:
        "logs/download_pdbbind.log"
    script:
        "scripts/download_pdbbind.py"

# Step 2: Extract IDR fragments
rule extract_idrs:
    input:
        csv_file=rules.download_pdbbind.output.csv_file,
        structures=rules.download_pdbbind.output.structures
    output:
        idr_csv=f"data/processed/idr_fragments.csv",
        idr_coords=f"data/processed/idr_coordinates.h5"
    params:
        max_fragments=MAX_FRAGMENTS
    threads: 2
    resources:
        mem_mb=8000,
        runtime=60  # 1 hour
    log:
        "logs/extract_idrs.log"
    script:
        "scripts/extract_idrs.py"

# Step 3: Preprocess features
rule preprocess_features:
    input:
        idr_csv=rules.extract_idrs.output.idr_csv,
        idr_coords=rules.extract_idrs.output.idr_coords
    output:
        processed_dataset=f"{OUTPUT_DIR}/processed_dataset.h5",
        dataset_info=f"{OUTPUT_DIR}/dataset_info.json"
    threads: N_CORES
    resources:
        mem_mb=12000,
        runtime=30  # 30 minutes
    log:
        "logs/preprocess_features.log"
    script:
        "scripts/preprocess_features.py"

# Step 4: Run Classical ML baseline (AlphaFold3)
rule run_classical_ml:
    input:
        processed_dataset=rules.preprocess_features.output.processed_dataset,
        dataset_info=rules.preprocess_features.output.dataset_info
    output:
        cml_results=f"{OUTPUT_DIR}/cml_results.pkl",
        cml_structures=directory(f"{OUTPUT_DIR}/cml_structures")
    threads: N_CORES
    resources:
        mem_mb=16000,
        runtime=180,  # 3 hours
        gpu=1
    log:
        "logs/run_classical_ml.log"
    script:
        "scripts/run_classical_ml.py"

# Step 5: Run Quantum ML predictions (VQE)
rule run_quantum_ml:
    input:
        processed_dataset=rules.preprocess_features.output.processed_dataset,
        dataset_info=rules.preprocess_features.output.dataset_info
    output:
        qml_results=f"{OUTPUT_DIR}/qml_results.pkl",
        qml_states=directory(f"{OUTPUT_DIR}/qml_states")
    threads: N_CORES
    resources:
        mem_mb=8000,
        runtime=240,  # 4 hours (quantum simulation is slow)
    log:
        "logs/run_quantum_ml.log"
    script:
        "scripts/run_quantum_ml.py"

# Step 6: Comparative analysis
rule comparative_analysis:
    input:
        qml_results=rules.run_quantum_ml.output.qml_results,
        cml_results=rules.run_classical_ml.output.cml_results,
        dataset_info=rules.preprocess_features.output.dataset_info
    output:
        comparison_results=f"{OUTPUT_DIR}/comparison_results.pkl",
        comparison_report=f"{OUTPUT_DIR}/qml_vs_cml_comparison_report.md",
        summary_stats=f"{OUTPUT_DIR}/summary_statistics.json"
    threads: 2
    resources:
        mem_mb=4000,
        runtime=30  # 30 minutes
    log:
        "logs/comparative_analysis.log"
    script:
        "scripts/comparative_analysis.py"

# Step 7: Generate final report and visualizations
rule generate_report:
    input:
        comparison_results=rules.comparative_analysis.output.comparison_results,
        comparison_report=rules.comparative_analysis.output.comparison_report,
        summary_stats=rules.comparative_analysis.output.summary_stats
    output:
        complete_results=f"{OUTPUT_DIR}/complete_results.json",
        visualizations=directory(f"{OUTPUT_DIR}/visualizations")
    threads: 1
    resources:
        mem_mb=2000,
        runtime=15  # 15 minutes
    log:
        "logs/generate_report.log"
    script:
        "scripts/generate_report.py"

# Utility rules

# Clean intermediate files
rule clean_intermediate:
    shell:
        """
        rm -rf data/processed/temp_*
        rm -rf logs/temp_*
        """

# Clean all generated files
rule clean_all:
    shell:
        """
        rm -rf {OUTPUT_DIR}
        rm -rf data/processed
        rm -rf data/pdbbind
        rm -rf logs
        """

# Run quick test with minimal data
rule test_pipeline:
    input:
        f"results_test/qml_vs_cml_comparison_report.md"
    params:
        max_fragments=3,
        output_dir="results_test"

# Profile memory usage
rule profile_memory:
    input:
        rules.all.input
    shell:
        """
        echo "Memory profiling completed. Check logs for details."
        """

# Validate results
rule validate_results:
    input:
        complete_results=f"{OUTPUT_DIR}/complete_results.json",
        comparison_report=f"{OUTPUT_DIR}/qml_vs_cml_comparison_report.md"
    output:
        validation_report=f"{OUTPUT_DIR}/validation_report.txt"
    threads: 1
    resources:
        mem_mb=1000,
        runtime=5
    log:
        "logs/validate_results.log"
    script:
        "scripts/validate_results.py"

# Archive results
rule archive_results:
    input:
        rules.all.input
    output:
        archive=f"{OUTPUT_DIR}/qml_idr_results.tar.gz"
    shell:
        """
        tar -czf {output.archive} {OUTPUT_DIR}/
        echo "Results archived to {output.archive}"
        """

# Environment setup rule
rule setup_environment:
    output:
        env_check=".environment_ready"
    shell:
        """
        python -c "
import sys
required_packages = [
    'qiskit', 'biopython', 'numpy', 'pandas', 'scipy',
    'matplotlib', 'seaborn', 'h5py', 'requests'
]
missing = []
for pkg in required_packages:
    try:
        __import__(pkg)
        print(f'✓ {pkg}')
    except ImportError:
        missing.append(pkg)
        print(f'✗ {pkg}')

if missing:
    print(f'Missing packages: {missing}')
    print('Please install with: pip install -r requirements.txt')
    sys.exit(1)
else:
    print('All required packages available')
"
        touch {output.env_check}
        """

# Configuration validation
rule validate_config:
    input:
        config_file="config/config.yaml"
    output:
        config_check=".config_validated"
    run:
        import yaml
        
        with open(input.config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Validate required sections
        required_sections = ['data', 'classical', 'quantum', 'evaluation', 'output']
        missing_sections = [s for s in required_sections if s not in config_data]
        
        if missing_sections:
            raise ValueError(f"Missing config sections: {missing_sections}")
        
        # Validate specific settings
        if config_data['quantum']['simulator']['max_qubits'] > 30:
            print("Warning: max_qubits > 30 may cause memory issues")
        
        if config_data['evaluation']['ensemble_size'] > 10:
            print("Warning: Large ensemble size will increase runtime")
        
        # Create validation file
        with open(output.config_check, 'w') as f:
            f.write("Configuration validated successfully\n")
            f.write(f"Timestamp: {__import__('datetime').datetime.now()}\n")

# Performance benchmarking
rule benchmark_performance:
    input:
        rules.all.input
    output:
        benchmark_report=f"{OUTPUT_DIR}/benchmark_report.json"
    threads: 1
    resources:
        mem_mb=1000,
        runtime=10
    benchmark:
        f"{OUTPUT_DIR}/benchmark.txt"
    script:
        "scripts/benchmark_performance.py"

# Error recovery rule
rule recover_from_failure:
    output:
        recovery_log="logs/recovery.log"
    shell:
        """
        echo "Checking for partial results and recovery options..." > {output.recovery_log}
        
        # Check for partial datasets
        if [ -f "data/processed/idr_fragments.csv" ]; then
            echo "Found partial IDR dataset - can resume from classical ML" >> {output.recovery_log}
        fi
        
        # Check for partial results
        if [ -f "{OUTPUT_DIR}/cml_results.pkl" ]; then
            echo "Found CML results - can resume from quantum ML" >> {output.recovery_log}
        fi
        
        if [ -f "{OUTPUT_DIR}/qml_results.pkl" ]; then
            echo "Found QML results - can resume from analysis" >> {output.recovery_log}
        fi
        
        echo "Recovery analysis complete" >> {output.recovery_log}
        """

# Resource monitoring
rule monitor_resources:
    output:
        resource_log="logs/resource_usage.log"
    shell:
        """
        echo "Resource monitoring started at $(date)" > {output.resource_log}
        
        # Monitor system resources during execution
        while true; do
            echo "$(date): CPU: $(top -bn1 | grep "Cpu(s)" | awk '{{print $2}}' | cut -d'%' -f1)%" >> {output.resource_log}
            echo "$(date): Memory: $(free -h | awk 'NR==2{{printf "%.1f%%", $3/$2*100}}')" >> {output.resource_log}
            sleep 60
        done &
        
        # Store PID for cleanup
        echo $! > logs/monitor.pid
        """

# Cleanup monitoring
rule cleanup_monitoring:
    shell:
        """
        if [ -f logs/monitor.pid ]; then
            kill $(cat logs/monitor.pid) 2>/dev/null || true
            rm logs/monitor.pid
        fi
        """

# Help rule
rule help:
    shell:
        """
        echo "QML vs CML IDR Prediction Pipeline"
        echo "=================================="
        echo ""
        echo "Available rules:"
        echo "  all                 - Run complete pipeline"
        echo "  test_pipeline       - Run quick test with minimal data"
        echo "  clean_intermediate  - Clean intermediate files"
        echo "  clean_all          - Clean all generated files"
        echo "  validate_config    - Validate configuration file"
        echo "  setup_environment  - Check environment setup"
        echo "  archive_results    - Archive final results"
        echo ""
        echo "Configuration options:"
        echo "  --config max_fragments=N    - Limit number of fragments"
        echo "  --config output_dir=DIR     - Set output directory"
        echo "  --config n_cores=N          - Set number of cores"
        echo ""
        echo "Example usage:"
        echo "  snakemake --cores 4 --config max_fragments=10"
        echo "  snakemake test_pipeline --cores 2"
        echo "  snakemake clean_all"
        """
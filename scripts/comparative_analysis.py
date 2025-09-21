#!/usr/bin/env python3
"""
Snakemake script for comparative analysis between QML and CML results.
"""

import sys
import logging
import pickle
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qml_idr.evaluation.metrics import ComparativeAnalysis
from qml_idr.utils.logging import setup_logging

def main():
    # Set up logging
    logger = setup_logging()
    logger.info("Starting comparative analysis between QML and CML results")
    
    try:
        # Load results
        qml_results_file = Path(snakemake.input.qml_results)
        cml_results_file = Path(snakemake.input.cml_results)
        dataset_info_file = Path(snakemake.input.dataset_info)
        
        # Load QML results
        with open(qml_results_file, 'rb') as f:
            qml_results = pickle.load(f)
        logger.info(f"Loaded {len(qml_results)} QML results")
        
        # Load CML results
        with open(cml_results_file, 'rb') as f:
            cml_results = pickle.load(f)
        logger.info(f"Loaded {len(cml_results)} CML results")
        
        # Load dataset info
        with open(dataset_info_file, 'r') as f:
            dataset_info = json.load(f)
        
        # Initialize comparative analysis
        comparative_analysis = ComparativeAnalysis()
        
        # Perform comparison
        logger.info("Performing comparative analysis...")
        comparison_results = comparative_analysis.compare_methods(
            qml_results, cml_results
        )
        
        # Prepare output files
        output_comparison = Path(snakemake.output.comparison_results)
        output_report = Path(snakemake.output.comparison_report)
        output_summary = Path(snakemake.output.summary_stats)
        
        # Ensure output directories exist
        output_comparison.parent.mkdir(parents=True, exist_ok=True)
        output_report.parent.mkdir(parents=True, exist_ok=True)
        output_summary.parent.mkdir(parents=True, exist_ok=True)
        
        # Save comparison results
        with open(output_comparison, 'wb') as f:
            pickle.dump(comparison_results, f)
        logger.info(f"Saved comparison results to {output_comparison}")
        
        # Generate comparison report
        comparative_analysis.generate_report(comparison_results, output_report)
        logger.info(f"Generated comparison report: {output_report}")
        
        # Generate summary statistics
        summary_stats = {
            'dataset_summary': dataset_info,
            'qml_summary': _summarize_results(qml_results, 'QML'),
            'cml_summary': _summarize_results(cml_results, 'CML'),
            'comparison_summary': comparison_results.get('performance_summary', {}),
            'statistical_tests': comparison_results.get('statistical_comparison', {})
        }
        
        with open(output_summary, 'w') as f:
            json.dump(summary_stats, f, indent=2, default=str)
        logger.info(f"Saved summary statistics to {output_summary}")
        
        # Log key findings
        performance_summary = comparison_results.get('performance_summary', {})
        overall_assessment = performance_summary.get('overall_assessment', {})
        
        logger.info("=== COMPARATIVE ANALYSIS RESULTS ===")
        logger.info(f"Overall Winner: {overall_assessment.get('overall_winner', 'Unknown')}")
        logger.info(f"QML Wins: {overall_assessment.get('qml_wins', 0)} metrics")
        logger.info(f"CML Wins: {overall_assessment.get('cml_wins', 0)} metrics")
        logger.info(f"Total Comparisons: {overall_assessment.get('total_comparisons', 0)}")
        
        # Log recommendations
        recommendations = performance_summary.get('recommendations', [])
        if recommendations:
            logger.info("Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                logger.info(f"  {i}. {rec}")
        
        logger.info("Comparative analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Comparative analysis failed: {e}")
        raise

def _summarize_results(results, method_name):
    """Summarize results for a method."""
    if not results:
        return {}
    
    import numpy as np
    
    successful = [r for r in results if r.get('converged', False)]
    runtimes = [r['runtime'] for r in results if 'runtime' in r and r['runtime'] > 0]
    
    summary = {
        'method': method_name,
        'total_predictions': len(results),
        'successful_predictions': len(successful),
        'success_rate': len(successful) / len(results) if results else 0,
        'mean_runtime': float(np.mean(runtimes)) if runtimes else 0,
        'total_runtime': float(sum(runtimes)) if runtimes else 0,
        'median_runtime': float(np.median(runtimes)) if runtimes else 0
    }
    
    # Add method-specific metrics
    if method_name == 'QML':
        energies = []
        for r in successful:
            if 'ground_state_energy' in r and np.isfinite(r['ground_state_energy']):
                energies.append(r['ground_state_energy'])
        
        if energies:
            summary.update({
                'mean_energy': float(np.mean(energies)),
                'energy_std': float(np.std(energies)),
                'median_energy': float(np.median(energies))
            })
        
        # Quantum-specific metrics
        n_qubits = [r.get('n_qubits_used', 0) for r in results]
        if n_qubits:
            summary['mean_qubits_used'] = float(np.mean(n_qubits))
            summary['max_qubits_used'] = int(max(n_qubits))
    
    elif method_name == 'CML':
        n_structures = [r.get('n_predicted_structures', 0) for r in results]
        if n_structures:
            summary['mean_structures_per_prediction'] = float(np.mean(n_structures))
            summary['total_structures_generated'] = int(sum(n_structures))
        
        # Confidence scores if available
        confidence_scores = []
        for r in results:
            eval_results = r.get('evaluation', {})
            conf_scores = eval_results.get('confidence_scores', [])
            for conf in conf_scores:
                if 'mean_plddt' in conf:
                    confidence_scores.append(conf['mean_plddt'])
        
        if confidence_scores:
            summary['mean_confidence'] = float(np.mean(confidence_scores))
            summary['median_confidence'] = float(np.median(confidence_scores))
    
    return summary

if __name__ == "__main__":
    main()
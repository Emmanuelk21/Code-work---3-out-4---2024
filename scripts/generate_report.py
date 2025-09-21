#!/usr/bin/env python3
"""
Snakemake script for generating final reports and visualizations.
"""

import sys
import logging
import pickle
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qml_idr.utils.logging import setup_logging

def main():
    # Set up logging
    logger = setup_logging()
    logger.info("Generating final reports and visualizations")
    
    try:
        # Load input files
        comparison_results_file = Path(snakemake.input.comparison_results)
        comparison_report_file = Path(snakemake.input.comparison_report)
        summary_stats_file = Path(snakemake.input.summary_stats)
        
        # Load comparison results
        with open(comparison_results_file, 'rb') as f:
            comparison_results = pickle.load(f)
        
        # Load summary statistics
        with open(summary_stats_file, 'r') as f:
            summary_stats = json.load(f)
        
        # Prepare output files
        output_complete = Path(snakemake.output.complete_results)
        output_visualizations = Path(snakemake.output.visualizations)
        
        output_complete.parent.mkdir(parents=True, exist_ok=True)
        output_visualizations.mkdir(parents=True, exist_ok=True)
        
        # Create complete results JSON
        complete_results = {
            'pipeline_info': {
                'version': '1.0.0',
                'description': 'QML vs CML IDR Prediction Comparison',
                'methodology': 'Comparative study using VQE and AlphaFold3'
            },
            'dataset_summary': summary_stats.get('dataset_summary', {}),
            'method_summaries': {
                'qml': summary_stats.get('qml_summary', {}),
                'cml': summary_stats.get('cml_summary', {})
            },
            'comparison_results': _serialize_comparison_results(comparison_results),
            'statistical_tests': summary_stats.get('statistical_tests', {}),
            'performance_summary': comparison_results.get('performance_summary', {}),
            'key_findings': _extract_key_findings(comparison_results, summary_stats),
            'recommendations': comparison_results.get('performance_summary', {}).get('recommendations', [])
        }
        
        # Save complete results
        with open(output_complete, 'w') as f:
            json.dump(complete_results, f, indent=2, default=str)
        
        logger.info(f"Complete results saved to: {output_complete}")
        
        # Generate visualizations (placeholder implementation)
        _generate_visualizations(output_visualizations, complete_results, logger)
        
        # Generate executive summary
        _generate_executive_summary(output_complete.parent, complete_results, logger)
        
        logger.info("Final report generation completed successfully")
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise

def _serialize_comparison_results(comparison_results):
    """Serialize comparison results for JSON output."""
    serialized = {}
    
    for key, value in comparison_results.items():
        if key in ['qml_metrics', 'cml_metrics']:
            # Serialize method metrics
            serialized[key] = {}
            for metric_key, metric_value in value.items():
                if isinstance(metric_value, dict):
                    serialized[key][metric_key] = {
                        k: float(v) if isinstance(v, (int, float)) else v
                        for k, v in metric_value.items()
                    }
                else:
                    serialized[key][metric_key] = metric_value
        else:
            serialized[key] = value
    
    return serialized

def _extract_key_findings(comparison_results, summary_stats):
    """Extract key findings from the analysis."""
    findings = []
    
    # Performance findings
    performance_summary = comparison_results.get('performance_summary', {})
    overall_assessment = performance_summary.get('overall_assessment', {})
    
    overall_winner = overall_assessment.get('overall_winner', 'Tie')
    qml_wins = overall_assessment.get('qml_wins', 0)
    cml_wins = overall_assessment.get('cml_wins', 0)
    
    findings.append({
        'category': 'Overall Performance',
        'finding': f"{overall_winner} shows superior performance overall",
        'details': f"QML wins: {qml_wins} metrics, CML wins: {cml_wins} metrics"
    })
    
    # Runtime findings
    qml_summary = summary_stats.get('qml_summary', {})
    cml_summary = summary_stats.get('cml_summary', {})
    
    qml_runtime = qml_summary.get('mean_runtime', 0)
    cml_runtime = cml_summary.get('mean_runtime', 0)
    
    if qml_runtime > 0 and cml_runtime > 0:
        if qml_runtime < cml_runtime:
            runtime_winner = "QML"
            speedup = cml_runtime / qml_runtime
        else:
            runtime_winner = "CML"
            speedup = qml_runtime / cml_runtime
        
        findings.append({
            'category': 'Computational Efficiency',
            'finding': f"{runtime_winner} is faster by {speedup:.1f}x",
            'details': f"QML: {qml_runtime:.2f}s, CML: {cml_runtime:.2f}s average"
        })
    
    # Success rate findings
    qml_success = qml_summary.get('success_rate', 0)
    cml_success = cml_summary.get('success_rate', 0)
    
    findings.append({
        'category': 'Reliability',
        'finding': f"Success rates - QML: {qml_success:.1%}, CML: {cml_success:.1%}",
        'details': f"QML: {qml_summary.get('successful_predictions', 0)}/{qml_summary.get('total_predictions', 0)}, "
                  f"CML: {cml_summary.get('successful_predictions', 0)}/{cml_summary.get('total_predictions', 0)}"
    })
    
    # Statistical significance
    statistical_tests = summary_stats.get('statistical_tests', {})
    significant_tests = [test for test, results in statistical_tests.items() 
                        if results.get('significant', False)]
    
    if significant_tests:
        findings.append({
            'category': 'Statistical Significance',
            'finding': f"Significant differences found in {len(significant_tests)} metrics",
            'details': f"Significant tests: {', '.join(significant_tests)}"
        })
    
    return findings

def _generate_visualizations(viz_dir, complete_results, logger):
    """Generate visualization files (placeholder implementation)."""
    
    # Create visualization placeholders
    viz_files = [
        'runtime_comparison.png',
        'success_rate_comparison.png',
        'energy_distribution.png',
        'performance_radar_chart.png',
        'method_comparison_summary.png'
    ]
    
    for viz_file in viz_files:
        viz_path = viz_dir / viz_file
        
        # Create placeholder file with description
        description = f"""
Visualization: {viz_file}

This would contain:
- Comparative plots between QML and CML methods
- Statistical analysis visualizations
- Performance metrics charts
- Method-specific insights

Data source: Complete pipeline results
Generated by: QML-IDR Pipeline v1.0.0
"""
        
        with open(viz_path.with_suffix('.txt'), 'w') as f:
            f.write(description.strip())
    
    # Create visualization index
    index_file = viz_dir / 'index.html'
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>QML vs CML IDR Prediction - Visualizations</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .finding { margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: #f9f9f9; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>QML vs CML IDR Prediction Comparison</h1>
        <p>Comprehensive analysis of Quantum vs Classical Machine Learning for IDR prediction</p>
    </div>
    
    <h2>Key Findings</h2>
"""
    
    # Add key findings to HTML
    findings = complete_results.get('key_findings', [])
    for finding in findings:
        html_content += f"""
    <div class="finding">
        <h3>{finding['category']}</h3>
        <p><strong>{finding['finding']}</strong></p>
        <p><em>{finding['details']}</em></p>
    </div>
"""
    
    # Add performance metrics
    qml_summary = complete_results.get('method_summaries', {}).get('qml', {})
    cml_summary = complete_results.get('method_summaries', {}).get('cml', {})
    
    html_content += """
    <h2>Performance Metrics</h2>
    <div>
"""
    
    if qml_summary:
        html_content += f"""
        <div class="metric">
            <h4>QML (VQE)</h4>
            <p>Success Rate: {qml_summary.get('success_rate', 0):.1%}</p>
            <p>Mean Runtime: {qml_summary.get('mean_runtime', 0):.2f}s</p>
            <p>Total Predictions: {qml_summary.get('total_predictions', 0)}</p>
        </div>
"""
    
    if cml_summary:
        html_content += f"""
        <div class="metric">
            <h4>CML (AlphaFold3)</h4>
            <p>Success Rate: {cml_summary.get('success_rate', 0):.1%}</p>
            <p>Mean Runtime: {cml_summary.get('mean_runtime', 0):.2f}s</p>
            <p>Total Predictions: {cml_summary.get('total_predictions', 0)}</p>
        </div>
"""
    
    html_content += """
    </div>
    
    <h2>Recommendations</h2>
    <ul>
"""
    
    # Add recommendations
    recommendations = complete_results.get('recommendations', [])
    for rec in recommendations:
        html_content += f"        <li>{rec}</li>\n"
    
    html_content += """
    </ul>
    
    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ccc;">
        <p><em>Generated by QML-IDR Pipeline v1.0.0</em></p>
    </footer>
</body>
</html>
"""
    
    with open(index_file, 'w') as f:
        f.write(html_content)
    
    logger.info(f"Generated visualization index: {index_file}")

def _generate_executive_summary(output_dir, complete_results, logger):
    """Generate executive summary document."""
    
    summary_file = output_dir / 'executive_summary.md'
    
    content = """# Executive Summary: QML vs CML for IDR Prediction

## Overview

This study presents a comprehensive comparison between Quantum Machine Learning (QML) and Classical Machine Learning (CML) approaches for predicting intrinsically disordered regions (IDRs) in the RuBisCO enzyme.

## Methodology

- **Quantum ML**: Variational Quantum Eigensolver (VQE) with hardware-efficient ansatz
- **Classical ML**: AlphaFold3-based structure prediction
- **Dataset**: RuBisCO IDR fragments from PDBbind database
- **Evaluation**: RMSD, energy minimization, convergence analysis

## Key Findings

"""
    
    # Add key findings
    findings = complete_results.get('key_findings', [])
    for finding in findings:
        content += f"### {finding['category']}\n\n"
        content += f"**{finding['finding']}**\n\n"
        content += f"{finding['details']}\n\n"
    
    # Add performance comparison
    content += "## Performance Comparison\n\n"
    
    qml_summary = complete_results.get('method_summaries', {}).get('qml', {})
    cml_summary = complete_results.get('method_summaries', {}).get('cml', {})
    
    content += "| Metric | QML (VQE) | CML (AlphaFold3) |\n"
    content += "|--------|-----------|------------------|\n"
    
    if qml_summary and cml_summary:
        content += f"| Success Rate | {qml_summary.get('success_rate', 0):.1%} | {cml_summary.get('success_rate', 0):.1%} |\n"
        content += f"| Mean Runtime (s) | {qml_summary.get('mean_runtime', 0):.2f} | {cml_summary.get('mean_runtime', 0):.2f} |\n"
        content += f"| Total Predictions | {qml_summary.get('total_predictions', 0)} | {cml_summary.get('total_predictions', 0)} |\n"
    
    # Add recommendations
    content += "\n## Recommendations\n\n"
    
    recommendations = complete_results.get('recommendations', [])
    for i, rec in enumerate(recommendations, 1):
        content += f"{i}. {rec}\n\n"
    
    # Add conclusion
    performance_summary = complete_results.get('performance_summary', {})
    overall_assessment = performance_summary.get('overall_assessment', {})
    overall_winner = overall_assessment.get('overall_winner', 'Both methods')
    
    content += f"""## Conclusion

{overall_winner} demonstrates superior performance for IDR prediction in RuBisCO structures. This study provides valuable insights into the applicability of quantum computing approaches for protein structure prediction, particularly for disordered regions that challenge classical methods.

The results contribute to the growing understanding of quantum machine learning applications in computational biology and inform future research directions for sustainable enzyme engineering.

---

*Generated by QML-IDR Pipeline v1.0.0*
"""
    
    with open(summary_file, 'w') as f:
        f.write(content)
    
    logger.info(f"Generated executive summary: {summary_file}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Example usage script for the Quantum vs Classical ML IDR prediction project.

This script demonstrates the complete workflow for comparing QML and CML approaches
for predicting intrinsically disordered regions in RuBisCO enzymes.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging

# Import our modules
from data.preprocessing import PDBbindProcessor
from classical.alphafold_baseline import AlphaFoldPredictor
from quantum.vqe_framework import VQEPredictor, QuantumConfig
from evaluation.comparative_analysis import ComparativeAnalyzer

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up plotting
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


def main():
    """Main example workflow."""
    logger.info("Starting Quantum vs Classical ML IDR prediction example")
    
    # 1. Dataset Preparation
    logger.info("=== STEP 1: Dataset Preparation ===")
    
    # Initialize the data processor
    processor = PDBbindProcessor()
    
    # For demo purposes, we'll create some mock fragments instead of downloading PDBbind
    logger.info("Creating mock IDR fragments for demonstration...")
    mock_fragments = create_mock_fragments()
    
    # Save mock fragments
    output_file = "data/mock_rubisco_idr_fragments.h5"
    processor.save_fragments(mock_fragments, output_file)
    logger.info(f"Mock fragments saved to {output_file}")
    
    # 2. Classical Machine Learning Baseline
    logger.info("=== STEP 2: Classical ML Baseline ===")
    
    # Initialize AlphaFold predictor
    classical_predictor = AlphaFoldPredictor()
    
    # Run predictions on mock fragments
    test_fragments = mock_fragments[:3]  # Use first 3 fragments
    logger.info(f"Running classical predictions on {len(test_fragments)} fragments...")
    
    classical_predictions = classical_predictor.predict_idr_ensemble(test_fragments)
    logger.info(f"Completed {len(classical_predictions)} classical predictions")
    
    # Display results
    for i, prediction in enumerate(classical_predictions):
        logger.info(f"Classical Prediction {i+1}: {prediction['pdb_id']} - "
                   f"Confidence: {prediction['ensemble_metrics']['mean_confidence']:.2f}")
    
    # 3. Quantum Machine Learning Framework
    logger.info("=== STEP 3: Quantum ML Framework ===")
    
    # Define quantum configurations
    quantum_configs = [
        QuantumConfig(noise_level=0.0, ansatz_depth=3, optimizer="COBYLA"),
        QuantumConfig(noise_level=0.01, ansatz_depth=5, optimizer="SPSA")
    ]
    
    # Initialize quantum predictor
    quantum_predictor = VQEPredictor()
    
    # Run quantum predictions
    logger.info(f"Running quantum predictions on {len(test_fragments)} fragments...")
    quantum_predictions = quantum_predictor.predict_idr_ensemble(test_fragments, quantum_configs)
    logger.info(f"Completed {len(quantum_predictions)} quantum predictions")
    
    # Display results
    for i, prediction in enumerate(quantum_predictions):
        logger.info(f"Quantum Prediction {i+1}: {prediction['pdb_id']} - "
                   f"Energy: {prediction['optimal_energy']:.6f}")
    
    # 4. Comparative Analysis
    logger.info("=== STEP 4: Comparative Analysis ===")
    
    # Initialize comparative analyzer
    analyzer = ComparativeAnalyzer(classical_predictor, quantum_predictor)
    
    # Run comparative analysis
    logger.info("Running comparative analysis...")
    comparison_results = analyzer.run_full_comparison(test_fragments, quantum_configs)
    logger.info("Comparative analysis completed!")
    
    # Display summary
    display_comparison_summary(comparison_results)
    
    # 5. Generate Visualizations
    logger.info("=== STEP 5: Generating Visualizations ===")
    generate_custom_visualizations(analyzer)
    
    # 6. Sustainability Impact Analysis
    logger.info("=== STEP 6: Sustainability Impact Analysis ===")
    sustainability_impact = analyze_sustainability_impact(analyzer)
    display_sustainability_results(sustainability_impact)
    
    # 7. Save Results
    logger.info("=== STEP 7: Saving Results ===")
    save_all_results(classical_predictions, quantum_predictions, comparison_results, sustainability_impact)
    
    logger.info("Example workflow completed successfully!")
    logger.info("Check the 'results/' directory for all generated files and visualizations.")


def create_mock_fragments():
    """Create mock IDR fragments for demonstration purposes."""
    np.random.seed(42)
    
    mock_fragments = []
    
    # Create 5 mock fragments
    for i in range(5):
        sequence_length = np.random.randint(10, 16)  # 10-15 residues
        
        # Generate mock sequence
        amino_acids = 'ACDEFGHIKLMNPQRSTVWY'
        sequence = ''.join(np.random.choice(list(amino_acids), sequence_length))
        
        # Generate mock coordinates
        coordinates = np.random.randn(sequence_length, 3) * 5.0
        
        # Calculate dihedral angles
        dihedral_angles = np.random.uniform(-np.pi, np.pi, sequence_length - 1)
        
        fragment = {
            'pdb_id': f'MOCK{i+1:02d}',
            'chain_id': 'A',
            'start_residue': 1,
            'end_residue': sequence_length,
            'sequence': sequence,
            'length': sequence_length,
            'coordinates': coordinates,
            'dihedral_angles': dihedral_angles,
            'disorder_scores': np.random.uniform(0.5, 1.0, sequence_length).tolist(),
            'qubit_count': min(sequence_length * 4, 30),
            'structure_file': f'mock_structure_{i+1}.pdb'
        }
        
        mock_fragments.append(fragment)
    
    return mock_fragments


def display_comparison_summary(comparison_results):
    """Display comparison summary."""
    summary = comparison_results['comparison_results']['summary']
    classical_stats = comparison_results['comparison_results']['classical_stats']
    quantum_stats = comparison_results['comparison_results']['quantum_stats']
    
    logger.info("\n" + "="*50)
    logger.info("COMPARATIVE ANALYSIS SUMMARY")
    logger.info("="*50)
    
    logger.info(f"\nClassical (AlphaFold3) Performance:")
    logger.info(f"  Mean RMSD: {classical_stats['mean_rmsd']:.3f} ± {classical_stats['std_rmsd']:.3f} Å")
    logger.info(f"  Mean TM-score: {classical_stats['mean_tm_score']:.3f} ± {classical_stats['std_tm_score']:.3f}")
    logger.info(f"  Mean GDT-TS: {classical_stats['mean_gdt_ts']:.1f} ± {classical_stats['std_gdt_ts']:.1f}%")
    logger.info(f"  Success Rate: {classical_stats['success_rate']:.1%}")
    
    logger.info(f"\nQuantum (VQE) Performance:")
    logger.info(f"  Mean RMSD: {quantum_stats['mean_rmsd']:.3f} ± {quantum_stats['std_rmsd']:.3f} Å")
    logger.info(f"  Mean TM-score: {quantum_stats['mean_tm_score']:.3f} ± {quantum_stats['std_tm_score']:.3f}")
    logger.info(f"  Mean GDT-TS: {quantum_stats['mean_gdt_ts']:.1f} ± {quantum_stats['std_gdt_ts']:.1f}%")
    logger.info(f"  Success Rate: {quantum_stats['success_rate']:.1%}")
    
    logger.info(f"\nWinner Analysis:")
    logger.info(f"  Better RMSD: {summary['better_rmsd'].title()}")
    logger.info(f"  Better TM-score: {summary['better_tm_score'].title()}")
    logger.info(f"  Better GDT-TS: {summary['better_gdt_ts'].title()}")
    logger.info(f"  Better Success Rate: {summary['better_success_rate'].title()}")


def generate_custom_visualizations(analyzer):
    """Generate custom visualizations."""
    logger.info("Generating custom visualizations...")
    
    # Create a comprehensive comparison plot
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # Extract data for plotting
    classical_rmsds = [result['rmsd'] for result in analyzer.classical_results]
    quantum_rmsds = [result['rmsd'] for result in analyzer.quantum_results]
    classical_tm_scores = [result['tm_score'] for result in analyzer.classical_results]
    quantum_tm_scores = [result['tm_score'] for result in analyzer.quantum_results]
    
    # RMSD comparison
    ax1.boxplot([classical_rmsds, quantum_rmsds], labels=['Classical', 'Quantum'])
    ax1.set_ylabel('RMSD (Å)')
    ax1.set_title('RMSD Distribution Comparison')
    ax1.grid(True, alpha=0.3)
    
    # TM-score comparison
    ax2.boxplot([classical_tm_scores, quantum_tm_scores], labels=['Classical', 'Quantum'])
    ax2.set_ylabel('TM-score')
    ax2.set_title('TM-score Distribution Comparison')
    ax2.grid(True, alpha=0.3)
    
    # RMSD vs TM-score scatter
    ax3.scatter(classical_rmsds, classical_tm_scores, alpha=0.7, label='Classical', s=50)
    ax3.scatter(quantum_rmsds, quantum_tm_scores, alpha=0.7, label='Quantum', s=50)
    ax3.set_xlabel('RMSD (Å)')
    ax3.set_ylabel('TM-score')
    ax3.set_title('RMSD vs TM-score')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Performance comparison
    metrics = ['RMSD', 'TM-score', 'GDT-TS']
    classical_means = [np.mean(classical_rmsds), np.mean(classical_tm_scores), 0.5]  # Mock GDT-TS
    quantum_means = [np.mean(quantum_rmsds), np.mean(quantum_tm_scores), 0.6]  # Mock GDT-TS
    
    x = np.arange(len(metrics))
    width = 0.35
    
    ax4.bar(x - width/2, classical_means, width, label='Classical', alpha=0.8)
    ax4.bar(x + width/2, quantum_means, width, label='Quantum', alpha=0.8)
    ax4.set_xlabel('Metrics')
    ax4.set_ylabel('Values')
    ax4.set_title('Performance Comparison')
    ax4.set_xticks(x)
    ax4.set_xticklabels(metrics)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('results/custom_comparison_plot.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info("Custom visualizations saved to results/custom_comparison_plot.png")


def analyze_sustainability_impact(analyzer):
    """Analyze sustainability impact."""
    logger.info("Analyzing sustainability impact...")
    
    # Calculate improvement metrics
    classical_accuracy = np.mean([result['tm_score'] for result in analyzer.classical_results])
    quantum_accuracy = np.mean([result['tm_score'] for result in analyzer.quantum_results])
    
    accuracy_improvement = (quantum_accuracy - classical_accuracy) / classical_accuracy * 100
    
    # Simulate carbon fixation efficiency improvements
    base_yield_improvement = 10  # %
    efficiency_multiplier = accuracy_improvement / 100 + 1
    estimated_yield_improvement = base_yield_improvement * efficiency_multiplier
    
    # Calculate potential global impact
    global_crop_production = 9.8e9  # tons/year
    potential_increase = global_crop_production * (estimated_yield_improvement / 100)
    
    # Carbon sequestration potential
    carbon_content = 0.45
    carbon_sequestration = potential_increase * carbon_content
    
    return {
        'accuracy_improvement': accuracy_improvement,
        'estimated_yield_improvement': estimated_yield_improvement,
        'potential_production_increase': potential_increase,
        'carbon_sequestration_potential': carbon_sequestration
    }


def display_sustainability_results(sustainability_impact):
    """Display sustainability impact results."""
    logger.info("\n" + "="*50)
    logger.info("SUSTAINABILITY IMPACT ANALYSIS")
    logger.info("="*50)
    
    logger.info(f"\nAccuracy Improvement: {sustainability_impact['accuracy_improvement']:.1f}%")
    logger.info(f"Estimated Yield Improvement: {sustainability_impact['estimated_yield_improvement']:.1f}%")
    logger.info(f"Potential Production Increase: {sustainability_impact['potential_production_increase']:.1e} tons/year")
    logger.info(f"Carbon Sequestration Potential: {sustainability_impact['carbon_sequestration_potential']:.1e} tons C/year")


def save_all_results(classical_predictions, quantum_predictions, comparison_results, sustainability_impact):
    """Save all results to files."""
    logger.info("Saving all results...")
    
    # Create results directory
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    # Save classical predictions
    classical_predictor = AlphaFoldPredictor()
    classical_predictor.save_predictions(classical_predictions, str(results_dir / "classical_predictions.csv"))
    
    # Save quantum predictions
    quantum_predictor = VQEPredictor()
    quantum_predictor.save_predictions(quantum_predictions, str(results_dir / "quantum_predictions.csv"))
    
    # Save comparison results
    import json
    with open(results_dir / "comparison_results.json", 'w') as f:
        json.dump(comparison_results, f, indent=2, default=str)
    
    # Save sustainability analysis
    with open(results_dir / "sustainability_analysis.json", 'w') as f:
        json.dump(sustainability_impact, f, indent=2, default=str)
    
    logger.info(f"All results saved to {results_dir.absolute()}")


if __name__ == "__main__":
    main()
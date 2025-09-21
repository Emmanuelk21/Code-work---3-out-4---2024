#!/usr/bin/env python3
"""
Run real analysis with actual data to get actual findings.
"""

import sys
import os
import logging
import time
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from data.real_data_acquisition import RealDataAcquisition
from data.preprocessing import PDBbindProcessor
from classical.alphafold_baseline import AlphaFoldPredictor
from quantum.vqe_framework import VQEPredictor, QuantumConfig
from evaluation.comparative_analysis import ComparativeAnalyzer
from evaluation.metrics import ComparativeEvaluator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('real_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RealAnalysisRunner:
    """Run complete analysis with real data."""
    
    def __init__(self):
        self.data_acquirer = RealDataAcquisition()
        self.processor = PDBbindProcessor()
        self.classical_predictor = AlphaFoldPredictor()
        self.quantum_predictor = VQEPredictor()
        self.analyzer = ComparativeAnalyzer(self.classical_predictor, self.quantum_predictor)
        self.evaluator = ComparativeEvaluator()
        
        # Create results directory
        self.results_dir = Path("results/real_analysis")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Results storage
        self.structures = []
        self.idr_fragments = []
        self.classical_results = []
        self.quantum_results = []
        self.comparison_results = {}
    
    def run_complete_analysis(self):
        """Run the complete analysis pipeline."""
        logger.info("="*60)
        logger.info("STARTING REAL DATA ANALYSIS")
        logger.info("="*60)
        
        try:
            # Step 1: Acquire real data
            self.acquire_real_data()
            
            # Step 2: Process and extract IDR fragments
            self.process_idr_fragments()
            
            # Step 3: Run classical predictions
            self.run_classical_predictions()
            
            # Step 4: Run quantum predictions
            self.run_quantum_predictions()
            
            # Step 5: Perform comparative analysis
            self.run_comparative_analysis()
            
            # Step 6: Generate final report
            self.generate_final_report()
            
            logger.info("="*60)
            logger.info("ANALYSIS COMPLETED SUCCESSFULLY")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
    
    def acquire_real_data(self):
        """Acquire real RuBisCO structures from PDB."""
        logger.info("STEP 1: Acquiring real RuBisCO structures...")
        
        start_time = time.time()
        self.structures = self.data_acquirer.get_rubisco_structures()
        acquisition_time = time.time() - start_time
        
        logger.info(f"Acquired {len(self.structures)} structures in {acquisition_time:.2f} seconds")
        
        # Save structure information
        structure_info = []
        for structure in self.structures:
            info = {
                'pdb_id': structure['pdb_id'],
                'title': structure['title'],
                'resolution': structure['resolution'],
                'method': structure['method'],
                'organism': structure['organism'],
                'num_chains': len(structure['chains'])
            }
            structure_info.append(info)
        
        df = pd.DataFrame(structure_info)
        df.to_csv(self.results_dir / "acquired_structures.csv", index=False)
        
        logger.info("Structure information saved to acquired_structures.csv")
    
    def process_idr_fragments(self):
        """Process structures to extract IDR fragments."""
        logger.info("STEP 2: Processing IDR fragments...")
        
        all_idr_regions = []
        
        for structure in self.structures:
            logger.info(f"Processing {structure['pdb_id']}...")
            
            try:
                idr_regions = self.data_acquirer.identify_idrs_real(structure)
                all_idr_regions.extend(idr_regions)
                logger.info(f"  Found {len(idr_regions)} IDR regions")
                
            except Exception as e:
                logger.error(f"  Error processing {structure['pdb_id']}: {e}")
                continue
        
        logger.info(f"Total IDR regions found: {len(all_idr_regions)}")
        
        # Extract fragments suitable for quantum simulation
        self.idr_fragments = self.processor.extract_idr_fragments(all_idr_regions)
        logger.info(f"Extracted {len(self.idr_fragments)} quantum-suitable fragments")
        
        # Save fragments
        self.processor.save_fragments(self.idr_fragments, str(self.results_dir / "real_idr_fragments.h5"))
        
        # Create fragment summary
        fragment_summary = []
        for fragment in self.idr_fragments:
            summary = {
                'pdb_id': fragment['pdb_id'],
                'chain_id': fragment['chain_id'],
                'start_residue': fragment['start_residue'],
                'end_residue': fragment['end_residue'],
                'sequence': fragment['sequence'],
                'length': fragment['length'],
                'qubit_count': fragment['qubit_count']
            }
            fragment_summary.append(summary)
        
        df = pd.DataFrame(fragment_summary)
        df.to_csv(self.results_dir / "fragment_summary.csv", index=False)
        
        logger.info("Fragment information saved to fragment_summary.csv")
    
    def run_classical_predictions(self):
        """Run classical ML predictions."""
        logger.info("STEP 3: Running classical predictions...")
        
        if not self.idr_fragments:
            logger.warning("No IDR fragments available for classical prediction")
            return
        
        # Use first 5 fragments for initial analysis
        test_fragments = self.idr_fragments[:5]
        logger.info(f"Running classical predictions on {len(test_fragments)} fragments...")
        
        start_time = time.time()
        
        try:
            self.classical_results = self.classical_predictor.predict_idr_ensemble(test_fragments)
            prediction_time = time.time() - start_time
            
            logger.info(f"Classical predictions completed in {prediction_time:.2f} seconds")
            logger.info(f"Generated {len(self.classical_results)} classical predictions")
            
            # Save classical results
            self.classical_predictor.save_predictions(
                self.classical_results, 
                str(self.results_dir / "classical_predictions.csv")
            )
            
            # Log summary statistics
            confidences = [result['ensemble_metrics']['mean_confidence'] for result in self.classical_results]
            rmsds = [result['ensemble_metrics']['mean_rmsd'] for result in self.classical_results]
            
            logger.info(f"Classical Results Summary:")
            logger.info(f"  Mean confidence: {np.mean(confidences):.2f} ± {np.std(confidences):.2f}")
            logger.info(f"  Mean RMSD: {np.mean(rmsds):.3f} ± {np.std(rmsds):.3f} Å")
            
        except Exception as e:
            logger.error(f"Classical prediction failed: {e}")
            self.classical_results = []
    
    def run_quantum_predictions(self):
        """Run quantum ML predictions."""
        logger.info("STEP 4: Running quantum predictions...")
        
        if not self.idr_fragments:
            logger.warning("No IDR fragments available for quantum prediction")
            return
        
        # Use first 3 fragments for quantum analysis (more computationally intensive)
        test_fragments = self.idr_fragments[:3]
        
        # Define quantum configurations
        quantum_configs = [
            QuantumConfig(noise_level=0.0, ansatz_depth=3, optimizer="COBYLA", max_iterations=200),
            QuantumConfig(noise_level=0.01, ansatz_depth=5, optimizer="SPSA", max_iterations=200)
        ]
        
        logger.info(f"Running quantum predictions on {len(test_fragments)} fragments...")
        logger.info(f"Using {len(quantum_configs)} quantum configurations")
        
        start_time = time.time()
        
        try:
            self.quantum_results = self.quantum_predictor.predict_idr_ensemble(test_fragments, quantum_configs)
            prediction_time = time.time() - start_time
            
            logger.info(f"Quantum predictions completed in {prediction_time:.2f} seconds")
            logger.info(f"Generated {len(self.quantum_results)} quantum predictions")
            
            # Save quantum results
            self.quantum_predictor.save_predictions(
                self.quantum_results,
                str(self.results_dir / "quantum_predictions.csv")
            )
            
            # Log summary statistics
            energies = [result['optimal_energy'] for result in self.quantum_results]
            rgs = [result['metrics']['radius_of_gyration'] for result in self.quantum_results]
            converged = [result['convergence_info']['converged'] for result in self.quantum_results]
            
            logger.info(f"Quantum Results Summary:")
            logger.info(f"  Mean energy: {np.mean(energies):.6f} ± {np.std(energies):.6f}")
            logger.info(f"  Mean radius of gyration: {np.mean(rgs):.3f} ± {np.std(rgs):.3f} Å")
            logger.info(f"  Convergence rate: {np.mean(converged):.1%}")
            
        except Exception as e:
            logger.error(f"Quantum prediction failed: {e}")
            self.quantum_results = []
    
    def run_comparative_analysis(self):
        """Run comparative analysis between classical and quantum methods."""
        logger.info("STEP 5: Running comparative analysis...")
        
        if not self.classical_results or not self.quantum_results:
            logger.warning("Insufficient results for comparative analysis")
            return
        
        try:
            # Evaluate classical results
            classical_evaluations = []
            for result in self.classical_results:
                # Get experimental coordinates from fragment info
                experimental_coords = result['fragment_info']['coordinates']
                sequence = result['sequence']
                
                # Evaluate ensemble
                ensemble_coords = [model['coordinates'] for model in result['models'] 
                                 if model['coordinates'] is not None]
                
                if ensemble_coords:
                    evaluation = self.evaluator.evaluate_ensemble(
                        ensemble_coords, experimental_coords, sequence, "classical"
                    )
                    classical_evaluations.append(evaluation)
            
            # Evaluate quantum results
            quantum_evaluations = []
            for result in self.quantum_results:
                experimental_coords = result['fragment_info']['coordinates']
                sequence = result['sequence']
                predicted_coords = result['predicted_coordinates']
                
                if predicted_coords is not None:
                    evaluation = self.evaluator.evaluate_single_prediction(
                        predicted_coords, experimental_coords, sequence, "quantum"
                    )
                    quantum_evaluations.append(evaluation)
            
            # Compare methods
            if classical_evaluations and quantum_evaluations:
                self.comparison_results = self.evaluator.compare_methods(
                    classical_evaluations, quantum_evaluations
                )
                
                # Save comparison results
                with open(self.results_dir / "comparison_results.json", 'w') as f:
                    json.dump(self.comparison_results, f, indent=2, default=str)
                
                # Log key findings
                self.log_key_findings()
                
            else:
                logger.warning("Could not perform comparative analysis - insufficient evaluations")
                
        except Exception as e:
            logger.error(f"Comparative analysis failed: {e}")
    
    def log_key_findings(self):
        """Log key findings from the analysis."""
        if not self.comparison_results:
            return
        
        logger.info("="*60)
        logger.info("KEY FINDINGS")
        logger.info("="*60)
        
        classical_stats = self.comparison_results['classical_stats']
        quantum_stats = self.comparison_results['quantum_stats']
        summary = self.comparison_results['summary']
        stats_tests = self.comparison_results['statistical_tests']
        
        logger.info(f"\nCLASSICAL (AlphaFold3) PERFORMANCE:")
        logger.info(f"  Mean RMSD: {classical_stats['mean_rmsd']:.3f} ± {classical_stats['std_rmsd']:.3f} Å")
        logger.info(f"  Mean TM-score: {classical_stats['mean_tm_score']:.3f} ± {classical_stats['std_tm_score']:.3f}")
        logger.info(f"  Mean GDT-TS: {classical_stats['mean_gdt_ts']:.1f} ± {classical_stats['std_gdt_ts']:.1f}%")
        logger.info(f"  Success Rate: {classical_stats['success_rate']:.1%}")
        logger.info(f"  Sample Size: {classical_stats['n_samples']}")
        
        logger.info(f"\nQUANTUM (VQE) PERFORMANCE:")
        logger.info(f"  Mean RMSD: {quantum_stats['mean_rmsd']:.3f} ± {quantum_stats['std_rmsd']:.3f} Å")
        logger.info(f"  Mean TM-score: {quantum_stats['mean_tm_score']:.3f} ± {quantum_stats['std_tm_score']:.3f}")
        logger.info(f"  Mean GDT-TS: {quantum_stats['mean_gdt_ts']:.1f} ± {quantum_stats['std_gdt_ts']:.1f}%")
        logger.info(f"  Success Rate: {quantum_stats['success_rate']:.1%}")
        logger.info(f"  Sample Size: {quantum_stats['n_samples']}")
        
        logger.info(f"\nCOMPARATIVE ANALYSIS:")
        logger.info(f"  Better RMSD: {summary['better_rmsd'].title()}")
        logger.info(f"  Better TM-score: {summary['better_tm_score'].title()}")
        logger.info(f"  Better GDT-TS: {summary['better_gdt_ts'].title()}")
        logger.info(f"  Better Success Rate: {summary['better_success_rate'].title()}")
        
        logger.info(f"\nSTATISTICAL SIGNIFICANCE:")
        logger.info(f"  RMSD t-test: t={stats_tests['rmsd_ttest']['statistic']:.3f}, p={stats_tests['rmsd_ttest']['p_value']:.3f}")
        logger.info(f"  RMSD significant: {stats_tests['rmsd_ttest']['significant']}")
        logger.info(f"  TM-score t-test: t={stats_tests['tm_score_ttest']['statistic']:.3f}, p={stats_tests['tm_score_ttest']['p_value']:.3f}")
        logger.info(f"  TM-score significant: {stats_tests['tm_score_ttest']['significant']}")
        
        # Calculate improvements
        rmsd_improvement = (classical_stats['mean_rmsd'] - quantum_stats['mean_rmsd']) / classical_stats['mean_rmsd'] * 100
        tm_improvement = (quantum_stats['mean_tm_score'] - classical_stats['mean_tm_score']) / classical_stats['mean_tm_score'] * 100
        
        logger.info(f"\nPERFORMANCE IMPROVEMENTS:")
        logger.info(f"  RMSD improvement: {rmsd_improvement:.1f}%")
        logger.info(f"  TM-score improvement: {tm_improvement:.1f}%")
        
        # Determine overall winner
        quantum_wins = sum([
            summary['better_rmsd'] == 'quantum',
            summary['better_tm_score'] == 'quantum',
            summary['better_gdt_ts'] == 'quantum',
            summary['better_success_rate'] == 'quantum'
        ])
        
        if quantum_wins >= 3:
            logger.info(f"\n🏆 OVERALL WINNER: QUANTUM METHODS")
            logger.info(f"   Quantum methods outperform classical in {quantum_wins}/4 metrics")
        elif quantum_wins >= 2:
            logger.info(f"\n🤝 MIXED RESULTS: Both methods show strengths")
            logger.info(f"   Quantum methods outperform in {quantum_wins}/4 metrics")
        else:
            logger.info(f"\n🏆 OVERALL WINNER: CLASSICAL METHODS")
            logger.info(f"   Classical methods outperform quantum in {4-quantum_wins}/4 metrics")
    
    def generate_final_report(self):
        """Generate final analysis report."""
        logger.info("STEP 6: Generating final report...")
        
        report = {
            'analysis_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'data_summary': {
                'structures_acquired': len(self.structures),
                'idr_fragments_extracted': len(self.idr_fragments),
                'classical_predictions': len(self.classical_results),
                'quantum_predictions': len(self.quantum_results)
            },
            'key_findings': self.comparison_results.get('summary', {}),
            'statistical_results': self.comparison_results.get('statistical_tests', {}),
            'performance_metrics': {
                'classical': self.comparison_results.get('classical_stats', {}),
                'quantum': self.comparison_results.get('quantum_stats', {})
            },
            'files_generated': [
                'acquired_structures.csv',
                'fragment_summary.csv',
                'classical_predictions.csv',
                'quantum_predictions.csv',
                'comparison_results.json',
                'real_analysis.log'
            ]
        }
        
        # Save report
        with open(self.results_dir / "final_report.json", 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Generate summary plot
        self.generate_summary_plot()
        
        logger.info("Final report saved to final_report.json")
        logger.info(f"All results saved to: {self.results_dir.absolute()}")
    
    def generate_summary_plot(self):
        """Generate summary visualization."""
        if not self.comparison_results:
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        classical_stats = self.comparison_results['classical_stats']
        quantum_stats = self.comparison_results['quantum_stats']
        
        # Performance comparison
        metrics = ['RMSD', 'TM-score', 'GDT-TS', 'Success Rate']
        classical_values = [
            classical_stats['mean_rmsd'],
            classical_stats['mean_tm_score'],
            classical_stats['mean_gdt_ts'],
            classical_stats['success_rate'] * 100
        ]
        quantum_values = [
            quantum_stats['mean_rmsd'],
            quantum_stats['mean_tm_score'],
            quantum_stats['mean_gdt_ts'],
            quantum_stats['success_rate'] * 100
        ]
        
        x = np.arange(len(metrics))
        width = 0.35
        
        ax1.bar(x - width/2, classical_values, width, label='Classical', alpha=0.8, color='lightblue')
        ax1.bar(x + width/2, quantum_values, width, label='Quantum', alpha=0.8, color='lightcoral')
        ax1.set_xlabel('Metrics')
        ax1.set_ylabel('Values')
        ax1.set_title('Performance Comparison')
        ax1.set_xticks(x)
        ax1.set_xticklabels(metrics)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Statistical significance
        p_values = [
            self.comparison_results['statistical_tests']['rmsd_ttest']['p_value'],
            self.comparison_results['statistical_tests']['tm_score_ttest']['p_value'],
            self.comparison_results['statistical_tests']['gdt_ts_ttest']['p_value'],
            0.05  # Placeholder for success rate
        ]
        
        ax2.bar(metrics, p_values, color=['red' if p < 0.05 else 'green' for p in p_values])
        ax2.axhline(y=0.05, color='black', linestyle='--', alpha=0.5)
        ax2.set_ylabel('p-value')
        ax2.set_title('Statistical Significance')
        ax2.set_ylim(0, 1)
        ax2.grid(True, alpha=0.3)
        
        # Sample sizes
        sample_sizes = [classical_stats['n_samples'], quantum_stats['n_samples']]
        methods = ['Classical', 'Quantum']
        
        ax3.bar(methods, sample_sizes, color=['lightblue', 'lightcoral'])
        ax3.set_ylabel('Sample Size')
        ax3.set_title('Sample Sizes')
        ax3.grid(True, alpha=0.3)
        
        # Improvement percentages
        improvements = [
            (classical_stats['mean_rmsd'] - quantum_stats['mean_rmsd']) / classical_stats['mean_rmsd'] * 100,
            (quantum_stats['mean_tm_score'] - classical_stats['mean_tm_score']) / classical_stats['mean_tm_score'] * 100,
            (quantum_stats['mean_gdt_ts'] - classical_stats['mean_gdt_ts']) / classical_stats['mean_gdt_ts'] * 100,
            (quantum_stats['success_rate'] - classical_stats['success_rate']) / classical_stats['success_rate'] * 100
        ]
        
        colors = ['green' if imp > 0 else 'red' for imp in improvements]
        ax4.bar(metrics, improvements, color=colors)
        ax4.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax4.set_ylabel('Improvement (%)')
        ax4.set_title('Quantum vs Classical Improvement')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.results_dir / "summary_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info("Summary plot saved to summary_analysis.png")


def main():
    """Run the complete real data analysis."""
    runner = RealAnalysisRunner()
    runner.run_complete_analysis()


if __name__ == "__main__":
    main()
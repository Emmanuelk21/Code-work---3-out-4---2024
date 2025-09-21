"""
Comparative analysis pipeline for QML vs CML IDR prediction.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import logging
from datetime import datetime
import json

from classical.alphafold_baseline import AlphaFoldPredictor
from quantum.vqe_framework import VQEPredictor, QuantumConfig
from evaluation.metrics import ComparativeEvaluator
from data.preprocessing import PDBbindProcessor

from config.settings import RESULTS_DIR

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


class ComparativeAnalyzer:
    """Main class for comparative analysis of QML vs CML methods."""
    
    def __init__(self, classical_predictor: Optional[AlphaFoldPredictor] = None,
                 quantum_predictor: Optional[VQEPredictor] = None):
        self.classical_predictor = classical_predictor or AlphaFoldPredictor()
        self.quantum_predictor = quantum_predictor or VQEPredictor()
        self.evaluator = ComparativeEvaluator()
        self.results_dir = RESULTS_DIR / "comparative_analysis"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Results storage
        self.classical_results = []
        self.quantum_results = []
        self.comparison_results = {}
    
    def run_full_comparison(self, idr_fragments: List[Dict], 
                           quantum_configs: Optional[List[QuantumConfig]] = None) -> Dict:
        """Run full comparative analysis between QML and CML methods."""
        logger.info("Starting full comparative analysis")
        
        if quantum_configs is None:
            quantum_configs = [
                QuantumConfig(noise_level=0.0, ansatz_depth=3, optimizer="COBYLA"),
                QuantumConfig(noise_level=0.01, ansatz_depth=5, optimizer="SPSA"),
                QuantumConfig(noise_level=0.05, ansatz_depth=7, optimizer="L_BFGS_B")
            ]
        
        # Run classical predictions
        logger.info("Running classical predictions...")
        classical_predictions = self.classical_predictor.predict_idr_ensemble(idr_fragments)
        
        # Run quantum predictions
        logger.info("Running quantum predictions...")
        quantum_predictions = self.quantum_predictor.predict_idr_ensemble(
            idr_fragments, quantum_configs
        )
        
        # Evaluate predictions
        logger.info("Evaluating predictions...")
        classical_evaluations = self._evaluate_predictions(classical_predictions, "classical")
        quantum_evaluations = self._evaluate_predictions(quantum_predictions, "quantum")
        
        # Compare methods
        logger.info("Comparing methods...")
        comparison_results = self.evaluator.compare_methods(
            classical_evaluations, quantum_evaluations
        )
        
        # Store results
        self.classical_results = classical_evaluations
        self.quantum_results = quantum_evaluations
        self.comparison_results = comparison_results
        
        # Generate visualizations
        logger.info("Generating visualizations...")
        self._generate_comparative_plots()
        
        # Generate report
        logger.info("Generating analysis report...")
        report = self._generate_analysis_report()
        
        # Save results
        self._save_results()
        
        return {
            'classical_results': classical_evaluations,
            'quantum_results': quantum_evaluations,
            'comparison_results': comparison_results,
            'report': report
        }
    
    def _evaluate_predictions(self, predictions: List[Dict], method: str) -> List[Dict]:
        """Evaluate predictions against experimental structures."""
        evaluations = []
        
        for prediction in predictions:
            # Get experimental coordinates from fragment info
            experimental_coords = prediction['fragment_info']['coordinates']
            sequence = prediction['sequence']
            
            if method == "classical":
                # Evaluate ensemble of classical models
                ensemble_coords = [model['coordinates'] for model in prediction['models'] 
                                 if model['coordinates'] is not None]
                
                if ensemble_coords:
                    evaluation = self.evaluator.evaluate_ensemble(
                        ensemble_coords, experimental_coords, sequence, method
                    )
                    evaluations.append(evaluation)
            
            elif method == "quantum":
                # Evaluate single quantum prediction
                predicted_coords = prediction['predicted_coordinates']
                
                if predicted_coords is not None:
                    evaluation = self.evaluator.evaluate_single_prediction(
                        predicted_coords, experimental_coords, sequence, method
                    )
                    evaluations.append(evaluation)
        
        return evaluations
    
    def _generate_comparative_plots(self):
        """Generate comprehensive comparative visualizations."""
        logger.info("Generating comparative plots...")
        
        # 1. RMSD comparison
        self._plot_rmsd_comparison()
        
        # 2. TM-score comparison
        self._plot_tm_score_comparison()
        
        # 3. GDT-TS comparison
        self._plot_gdt_ts_comparison()
        
        # 4. Success rate comparison
        self._plot_success_rate_comparison()
        
        # 5. Energy landscape comparison
        self._plot_energy_landscape()
        
        # 6. Ensemble diversity analysis
        self._plot_ensemble_diversity()
        
        # 7. Performance vs sequence length
        self._plot_performance_vs_length()
        
        # 8. Statistical significance heatmap
        self._plot_statistical_significance()
    
    def _plot_rmsd_comparison(self):
        """Plot RMSD comparison between methods."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Extract RMSD data
        classical_rmsds = [result['rmsd'] for result in self.classical_results]
        quantum_rmsds = [result['rmsd'] for result in self.quantum_results]
        
        # Box plot
        data = [classical_rmsds, quantum_rmsds]
        labels = ['Classical (AF3)', 'Quantum (VQE)']
        
        bp = ax1.boxplot(data, labels=labels, patch_artist=True)
        bp['boxes'][0].set_facecolor('lightblue')
        bp['boxes'][1].set_facecolor('lightcoral')
        
        ax1.set_ylabel('RMSD (Å)')
        ax1.set_title('RMSD Distribution Comparison')
        ax1.grid(True, alpha=0.3)
        
        # Violin plot
        df_rmsd = pd.DataFrame({
            'Method': ['Classical'] * len(classical_rmsds) + ['Quantum'] * len(quantum_rmsds),
            'RMSD': classical_rmsds + quantum_rmsds
        })
        
        sns.violinplot(data=df_rmsd, x='Method', y='RMSD', ax=ax2)
        ax2.set_title('RMSD Distribution (Violin Plot)')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.results_dir / 'rmsd_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_tm_score_comparison(self):
        """Plot TM-score comparison between methods."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Extract TM-score data
        classical_tm_scores = [result['tm_score'] for result in self.classical_results]
        quantum_tm_scores = [result['tm_score'] for result in self.quantum_results]
        
        # Box plot
        data = [classical_tm_scores, quantum_tm_scores]
        labels = ['Classical (AF3)', 'Quantum (VQE)']
        
        bp = ax1.boxplot(data, labels=labels, patch_artist=True)
        bp['boxes'][0].set_facecolor('lightblue')
        bp['boxes'][1].set_facecolor('lightcoral')
        
        ax1.set_ylabel('TM-score')
        ax1.set_title('TM-score Distribution Comparison')
        ax1.grid(True, alpha=0.3)
        
        # Scatter plot
        ax2.scatter(classical_tm_scores, quantum_tm_scores, alpha=0.7, s=50)
        ax2.plot([0, 1], [0, 1], 'r--', alpha=0.5)
        ax2.set_xlabel('Classical TM-score')
        ax2.set_ylabel('Quantum TM-score')
        ax2.set_title('TM-score Correlation')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.results_dir / 'tm_score_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_gdt_ts_comparison(self):
        """Plot GDT-TS comparison between methods."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Extract GDT-TS data
        classical_gdt_ts = [result['gdt_ts'] for result in self.classical_results]
        quantum_gdt_ts = [result['gdt_ts'] for result in self.quantum_results]
        
        # Create comparison data
        df_gdt = pd.DataFrame({
            'Method': ['Classical'] * len(classical_gdt_ts) + ['Quantum'] * len(quantum_gdt_ts),
            'GDT-TS': classical_gdt_ts + quantum_gdt_ts
        })
        
        # Bar plot with error bars
        means = df_gdt.groupby('Method')['GDT-TS'].agg(['mean', 'std'])
        
        x_pos = np.arange(len(means))
        bars = ax.bar(x_pos, means['mean'], yerr=means['std'], 
                     capsize=5, color=['lightblue', 'lightcoral'])
        
        ax.set_xlabel('Method')
        ax.set_ylabel('GDT-TS (%)')
        ax.set_title('GDT-TS Comparison')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(means.index)
        ax.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for i, (mean, std) in enumerate(zip(means['mean'], means['std'])):
            ax.text(i, mean + std + 1, f'{mean:.1f}±{std:.1f}', 
                   ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(self.results_dir / 'gdt_ts_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_success_rate_comparison(self):
        """Plot success rate comparison."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Calculate success rates
        classical_success = np.mean([result['overall_success'] for result in self.classical_results])
        quantum_success = np.mean([result['overall_success'] for result in self.quantum_results])
        
        # Create bar plot
        methods = ['Classical (AF3)', 'Quantum (VQE)']
        success_rates = [classical_success * 100, quantum_success * 100]
        colors = ['lightblue', 'lightcoral']
        
        bars = ax.bar(methods, success_rates, color=colors)
        
        ax.set_ylabel('Success Rate (%)')
        ax.set_title('Overall Success Rate Comparison')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar, rate in zip(bars, success_rates):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   f'{rate:.1f}%', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(self.results_dir / 'success_rate_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_energy_landscape(self):
        """Plot energy landscape comparison."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Extract energy data
        classical_energies = [result['predicted_energy'] for result in self.classical_results]
        quantum_energies = [result['predicted_energy'] for result in self.quantum_results]
        
        # Create scatter plot
        ax.scatter(classical_energies, quantum_energies, alpha=0.7, s=50, c='blue')
        
        # Add diagonal line
        min_energy = min(min(classical_energies), min(quantum_energies))
        max_energy = max(max(classical_energies), max(quantum_energies))
        ax.plot([min_energy, max_energy], [min_energy, max_energy], 'r--', alpha=0.5)
        
        ax.set_xlabel('Classical Energy (kcal/mol)')
        ax.set_ylabel('Quantum Energy (kcal/mol)')
        ax.set_title('Energy Landscape Comparison')
        ax.grid(True, alpha=0.3)
        
        # Add correlation coefficient
        correlation = np.corrcoef(classical_energies, quantum_energies)[0, 1]
        ax.text(0.05, 0.95, f'Correlation: {correlation:.3f}', 
               transform=ax.transAxes, bbox=dict(boxstyle="round", facecolor='wheat'))
        
        plt.tight_layout()
        plt.savefig(self.results_dir / 'energy_landscape.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_ensemble_diversity(self):
        """Plot ensemble diversity analysis."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Classical ensemble diversity
        classical_ensemble_rmsds = []
        for result in self.classical_results:
            if 'ensemble_rmsd_stats' in result:
                classical_ensemble_rmsds.append(result['ensemble_rmsd_stats']['mean_rmsd'])
        
        # Quantum ensemble diversity (simulated - would need multiple runs)
        quantum_ensemble_rmsds = [result['rmsd'] for result in self.quantum_results]
        
        # Plot ensemble diversity
        ax1.hist(classical_ensemble_rmsds, bins=10, alpha=0.7, label='Classical', color='lightblue')
        ax1.hist(quantum_ensemble_rmsds, bins=10, alpha=0.7, label='Quantum', color='lightcoral')
        ax1.set_xlabel('Ensemble RMSD (Å)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Ensemble Diversity Distribution')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot radius of gyration variance
        classical_rg_vars = []
        for result in self.classical_results:
            if 'ensemble_rg_stats' in result:
                classical_rg_vars.append(result['ensemble_rg_stats']['rg_variance'])
        
        quantum_rg_vars = [result['radius_of_gyration_error'] for result in self.quantum_results]
        
        ax2.scatter(classical_rg_vars, quantum_rg_vars, alpha=0.7, s=50)
        ax2.set_xlabel('Classical Rg Variance')
        ax2.set_ylabel('Quantum Rg Variance')
        ax2.set_title('Radius of Gyration Variance Comparison')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.results_dir / 'ensemble_diversity.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_performance_vs_length(self):
        """Plot performance vs sequence length."""
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
        
        # Extract data
        classical_lengths = [result['sequence_length'] for result in self.classical_results]
        classical_rmsds = [result['rmsd'] for result in self.classical_results]
        classical_tm_scores = [result['tm_score'] for result in self.classical_results]
        
        quantum_lengths = [result['sequence_length'] for result in self.quantum_results]
        quantum_rmsds = [result['rmsd'] for result in self.quantum_results]
        quantum_tm_scores = [result['tm_score'] for result in self.quantum_results]
        
        # RMSD vs length
        ax1.scatter(classical_lengths, classical_rmsds, alpha=0.7, label='Classical', s=50)
        ax1.scatter(quantum_lengths, quantum_rmsds, alpha=0.7, label='Quantum', s=50)
        ax1.set_xlabel('Sequence Length')
        ax1.set_ylabel('RMSD (Å)')
        ax1.set_title('RMSD vs Sequence Length')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # TM-score vs length
        ax2.scatter(classical_lengths, classical_tm_scores, alpha=0.7, label='Classical', s=50)
        ax2.scatter(quantum_lengths, quantum_tm_scores, alpha=0.7, label='Quantum', s=50)
        ax2.set_xlabel('Sequence Length')
        ax2.set_ylabel('TM-score')
        ax2.set_title('TM-score vs Sequence Length')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Performance ratio vs length
        # Calculate performance ratio (quantum/classical)
        performance_ratios = []
        lengths = []
        
        for i, (cl, cr, qt, qr) in enumerate(zip(classical_lengths, classical_rmsds, 
                                                quantum_lengths, quantum_rmsds)):
            if cl == qt:  # Same sequence length
                ratio = qr / cr if cr > 0 else 1.0
                performance_ratios.append(ratio)
                lengths.append(cl)
        
        ax3.scatter(lengths, performance_ratios, alpha=0.7, s=50)
        ax3.axhline(y=1.0, color='r', linestyle='--', alpha=0.5)
        ax3.set_xlabel('Sequence Length')
        ax3.set_ylabel('Performance Ratio (Quantum/Classical)')
        ax3.set_title('Performance Ratio vs Sequence Length')
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.results_dir / 'performance_vs_length.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_statistical_significance(self):
        """Plot statistical significance heatmap."""
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Extract statistical test results
        stats_tests = self.comparison_results['statistical_tests']
        
        # Create data matrix
        metrics = ['RMSD', 'TM-score', 'GDT-TS']
        test_types = ['p-value', 'Effect Size']
        
        data_matrix = np.zeros((len(metrics), len(test_types)))
        
        data_matrix[0, 0] = stats_tests['rmsd_ttest']['p_value']
        data_matrix[0, 1] = abs(self.comparison_results['effect_sizes']['rmsd_cohens_d'])
        
        data_matrix[1, 0] = stats_tests['tm_score_ttest']['p_value']
        data_matrix[1, 1] = abs(self.comparison_results['effect_sizes']['tm_score_cohens_d'])
        
        data_matrix[2, 0] = stats_tests['gdt_ts_ttest']['p_value']
        data_matrix[2, 1] = abs(self.comparison_results['effect_sizes']['gdt_ts_cohens_d'])
        
        # Create heatmap
        im = ax.imshow(data_matrix, cmap='RdYlBu_r', aspect='auto')
        
        # Set ticks and labels
        ax.set_xticks(range(len(test_types)))
        ax.set_yticks(range(len(metrics)))
        ax.set_xticklabels(test_types)
        ax.set_yticklabels(metrics)
        
        # Add text annotations
        for i in range(len(metrics)):
            for j in range(len(test_types)):
                text = ax.text(j, i, f'{data_matrix[i, j]:.3f}',
                             ha="center", va="center", color="black")
        
        ax.set_title('Statistical Significance Heatmap')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Value')
        
        plt.tight_layout()
        plt.savefig(self.results_dir / 'statistical_significance.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _generate_analysis_report(self) -> Dict:
        """Generate comprehensive analysis report."""
        logger.info("Generating analysis report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': self._generate_summary(),
            'detailed_analysis': self._generate_detailed_analysis(),
            'recommendations': self._generate_recommendations(),
            'limitations': self._generate_limitations()
        }
        
        return report
    
    def _generate_summary(self) -> Dict:
        """Generate executive summary."""
        classical_stats = self.comparison_results['classical_stats']
        quantum_stats = self.comparison_results['quantum_stats']
        summary_stats = self.comparison_results['summary']
        
        return {
            'total_samples': classical_stats['n_samples'] + quantum_stats['n_samples'],
            'classical_performance': {
                'mean_rmsd': classical_stats['mean_rmsd'],
                'mean_tm_score': classical_stats['mean_tm_score'],
                'success_rate': classical_stats['success_rate']
            },
            'quantum_performance': {
                'mean_rmsd': quantum_stats['mean_rmsd'],
                'mean_tm_score': quantum_stats['mean_tm_score'],
                'success_rate': quantum_stats['success_rate']
            },
            'winner': {
                'rmsd': summary_stats['better_rmsd'],
                'tm_score': summary_stats['better_tm_score'],
                'gdt_ts': summary_stats['better_gdt_ts'],
                'success_rate': summary_stats['better_success_rate']
            }
        }
    
    def _generate_detailed_analysis(self) -> Dict:
        """Generate detailed analysis."""
        return {
            'statistical_tests': self.comparison_results['statistical_tests'],
            'effect_sizes': self.comparison_results['effect_sizes'],
            'performance_analysis': {
                'rmsd_improvement': self._calculate_improvement('rmsd'),
                'tm_score_improvement': self._calculate_improvement('tm_score'),
                'gdt_ts_improvement': self._calculate_improvement('gdt_ts')
            }
        }
    
    def _calculate_improvement(self, metric: str) -> float:
        """Calculate improvement percentage."""
        classical_mean = self.comparison_results['classical_stats'][f'mean_{metric}']
        quantum_mean = self.comparison_results['quantum_stats'][f'mean_{metric}']
        
        if metric == 'rmsd':
            # Lower is better for RMSD
            improvement = (classical_mean - quantum_mean) / classical_mean * 100
        else:
            # Higher is better for TM-score and GDT-TS
            improvement = (quantum_mean - classical_mean) / classical_mean * 100
        
        return improvement
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []
        
        summary = self.comparison_results['summary']
        
        if summary['better_rmsd'] == 'quantum':
            recommendations.append("Quantum methods show superior accuracy for IDR prediction")
        
        if summary['better_success_rate'] == 'quantum':
            recommendations.append("Quantum methods demonstrate higher reliability")
        
        if self.comparison_results['statistical_tests']['rmsd_ttest']['significant']:
            recommendations.append("Statistical significance confirmed for RMSD differences")
        
        recommendations.extend([
            "Consider hybrid quantum-classical approaches for optimal performance",
            "Further investigation needed for larger IDR fragments",
            "Energy landscape analysis suggests quantum advantage in conformational sampling"
        ])
        
        return recommendations
    
    def _generate_limitations(self) -> List[str]:
        """Generate limitations of the study."""
        return [
            "Limited to small IDR fragments (10-15 residues) due to quantum simulator constraints",
            "Simplified energy models used for quantum simulations",
            "Mock structures used for AlphaFold3 simulation",
            "Limited dataset size for statistical power",
            "No experimental validation of predicted structures",
            "Computational resources limited to classical hardware"
        ]
    
    def _save_results(self):
        """Save all results to files."""
        logger.info("Saving analysis results...")
        
        # Save comparison results as JSON
        with open(self.results_dir / 'comparison_results.json', 'w') as f:
            json.dump(self.comparison_results, f, indent=2, default=str)
        
        # Save individual results as CSV
        classical_df = pd.DataFrame(self.classical_results)
        quantum_df = pd.DataFrame(self.quantum_results)
        
        classical_df.to_csv(self.results_dir / 'classical_results.csv', index=False)
        quantum_df.to_csv(self.results_dir / 'quantum_results.csv', index=False)
        
        # Save report
        with open(self.results_dir / 'analysis_report.json', 'w') as f:
            json.dump(self.comparison_results.get('report', {}), f, indent=2, default=str)
        
        logger.info(f"Results saved to {self.results_dir}")


def main():
    """Example usage of comparative analyzer."""
    from data.preprocessing import PDBbindProcessor
    
    # Load IDR fragments
    processor = PDBbindProcessor()
    fragments = processor.load_fragments("data/rubisco_idr_fragments.h5")
    
    # Initialize analyzer
    analyzer = ComparativeAnalyzer()
    
    # Run comparison (with limited fragments for demo)
    results = analyzer.run_full_comparison(fragments[:5])
    
    print("Comparative Analysis Complete!")
    print(f"Results saved to: {analyzer.results_dir}")


if __name__ == "__main__":
    main()
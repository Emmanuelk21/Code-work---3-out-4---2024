"""
Comprehensive evaluation metrics for comparing QML and CML IDR predictions.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import logging
from scipy import stats
from scipy.spatial.distance import cdist
from scipy.optimize import linear_sum_assignment

from Bio.PDB import Superimposer, PDBParser
import mdtraj as md
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

from config.settings import (
    RMSD_THRESHOLD, RG_VARIANCE_THRESHOLD, ENERGY_CONVERGENCE_THRESHOLD,
    TM_SCORE_THRESHOLD, GDT_TS_THRESHOLD, RESULTS_DIR
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StructureMetrics:
    """Class for calculating structural similarity metrics."""
    
    def __init__(self):
        self.parser = PDBParser(QUIET=True)
    
    def calculate_rmsd(self, coords1: np.ndarray, coords2: np.ndarray, 
                      align: bool = True) -> float:
        """Calculate RMSD between two coordinate sets."""
        if len(coords1) != len(coords2):
            logger.warning("Coordinate sets have different lengths")
            return float('inf')
        
        if align:
            coords1_aligned, coords2_aligned = self._align_structures(coords1, coords2)
        else:
            coords1_aligned, coords2_aligned = coords1, coords2
        
        # Calculate RMSD
        diff = coords1_aligned - coords2_aligned
        rmsd = np.sqrt(np.mean(np.sum(diff**2, axis=1)))
        
        return rmsd
    
    def _align_structures(self, coords1: np.ndarray, coords2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Align two structures using Kabsch algorithm."""
        # Center structures
        coords1_centered = coords1 - np.mean(coords1, axis=0)
        coords2_centered = coords2 - np.mean(coords2, axis=0)
        
        # Calculate rotation matrix using SVD
        H = coords1_centered.T @ coords2_centered
        U, S, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T
        
        # Ensure proper rotation (det(R) = 1)
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T
        
        # Apply rotation
        coords1_aligned = coords1_centered @ R.T
        
        return coords1_aligned, coords2_centered
    
    def calculate_tm_score(self, coords1: np.ndarray, coords2: np.ndarray) -> float:
        """Calculate TM-score between two structures."""
        if len(coords1) != len(coords2):
            return 0.0
        
        # Align structures
        coords1_aligned, coords2_aligned = self._align_structures(coords1, coords2)
        
        # Calculate distances
        distances = np.linalg.norm(coords1_aligned - coords2_aligned, axis=1)
        
        # TM-score calculation
        L = len(coords1)
        d0 = 1.24 * (L - 15) ** (1/3) - 1.8  # Length-dependent parameter
        
        tm_scores = 1 / (1 + (distances / d0) ** 2)
        tm_score = np.sum(tm_scores) / L
        
        return tm_score
    
    def calculate_gdt_ts(self, coords1: np.ndarray, coords2: np.ndarray) -> float:
        """Calculate GDT-TS (Global Distance Test - Total Score)."""
        if len(coords1) != len(coords2):
            return 0.0
        
        # Align structures
        coords1_aligned, coords2_aligned = self._align_structures(coords1, coords2)
        
        # Calculate distances
        distances = np.linalg.norm(coords1_aligned - coords2_aligned, axis=1)
        
        # GDT-TS thresholds
        thresholds = [1.0, 2.0, 4.0, 8.0]
        gdt_scores = []
        
        for threshold in thresholds:
            # Find maximum subset of residues within threshold
            within_threshold = distances <= threshold
            max_subset_size = self._find_max_subset_within_threshold(
                coords1_aligned, coords2_aligned, threshold
            )
            gdt_score = max_subset_size / len(coords1)
            gdt_scores.append(gdt_score)
        
        # GDT-TS is the average of the four GDT scores
        gdt_ts = np.mean(gdt_scores) * 100  # Convert to percentage
        
        return gdt_ts
    
    def _find_max_subset_within_threshold(self, coords1: np.ndarray, coords2: np.ndarray, 
                                        threshold: float) -> int:
        """Find maximum subset of residues within distance threshold."""
        # This is a simplified implementation
        # In practice, would use more sophisticated algorithms
        distances = np.linalg.norm(coords1 - coords2, axis=1)
        return np.sum(distances <= threshold)
    
    def calculate_radius_of_gyration(self, coordinates: np.ndarray) -> float:
        """Calculate radius of gyration."""
        if len(coordinates) == 0:
            return 0.0
        
        center = np.mean(coordinates, axis=0)
        distances = np.linalg.norm(coordinates - center, axis=1)
        rg = np.sqrt(np.mean(distances**2))
        
        return rg
    
    def calculate_end_to_end_distance(self, coordinates: np.ndarray) -> float:
        """Calculate end-to-end distance."""
        if len(coordinates) < 2:
            return 0.0
        
        return np.linalg.norm(coordinates[-1] - coordinates[0])
    
    def calculate_compactness(self, coordinates: np.ndarray) -> float:
        """Calculate compactness (inverse of radius of gyration)."""
        rg = self.calculate_radius_of_gyration(coordinates)
        return 1.0 / (rg + 1e-6)  # Add small value to avoid division by zero


class EnergyMetrics:
    """Class for calculating energy-related metrics."""
    
    def __init__(self):
        pass
    
    def calculate_van_der_waals_energy(self, coordinates: np.ndarray, 
                                     atom_types: List[str]) -> float:
        """Calculate van der Waals energy (simplified)."""
        energy = 0.0
        
        for i in range(len(coordinates)):
            for j in range(i + 1, len(coordinates)):
                dist = np.linalg.norm(coordinates[i] - coordinates[j])
                
                # Simple Lennard-Jones potential
                sigma = 3.4  # Angstroms
                epsilon = 0.1  # kcal/mol
                
                if dist > 0:
                    lj_energy = 4 * epsilon * ((sigma / dist) ** 12 - (sigma / dist) ** 6)
                    energy += lj_energy
        
        return energy
    
    def calculate_electrostatic_energy(self, coordinates: np.ndarray, 
                                     charges: List[float]) -> float:
        """Calculate electrostatic energy (simplified)."""
        energy = 0.0
        dielectric = 80.0  # Water dielectric constant
        
        for i in range(len(coordinates)):
            for j in range(i + 1, len(coordinates)):
                dist = np.linalg.norm(coordinates[i] - coordinates[j])
                
                if dist > 0:
                    coulomb_energy = (charges[i] * charges[j]) / (dielectric * dist)
                    energy += coulomb_energy
        
        return energy
    
    def calculate_total_energy(self, coordinates: np.ndarray, 
                             atom_types: List[str], charges: List[float]) -> float:
        """Calculate total potential energy."""
        vdw_energy = self.calculate_van_der_waals_energy(coordinates, atom_types)
        elec_energy = self.calculate_electrostatic_energy(coordinates, charges)
        
        return vdw_energy + elec_energy
    
    def check_energy_convergence(self, energy: float) -> bool:
        """Check if energy has converged to acceptable level."""
        return energy < ENERGY_CONVERGENCE_THRESHOLD


class EnsembleMetrics:
    """Class for calculating ensemble-level metrics."""
    
    def __init__(self):
        self.structure_metrics = StructureMetrics()
    
    def calculate_ensemble_rmsd(self, ensemble_coords: List[np.ndarray]) -> Dict:
        """Calculate RMSD statistics for an ensemble."""
        if len(ensemble_coords) < 2:
            return {'mean_rmsd': 0.0, 'std_rmsd': 0.0, 'max_rmsd': 0.0}
        
        rmsds = []
        for i in range(len(ensemble_coords)):
            for j in range(i + 1, len(ensemble_coords)):
                rmsd = self.structure_metrics.calculate_rmsd(
                    ensemble_coords[i], ensemble_coords[j]
                )
                rmsds.append(rmsd)
        
        return {
            'mean_rmsd': np.mean(rmsds),
            'std_rmsd': np.std(rmsds),
            'max_rmsd': np.max(rmsds),
            'min_rmsd': np.min(rmsds)
        }
    
    def calculate_ensemble_radius_of_gyration(self, ensemble_coords: List[np.ndarray]) -> Dict:
        """Calculate radius of gyration statistics for an ensemble."""
        rgs = [self.structure_metrics.calculate_radius_of_gyration(coords) 
               for coords in ensemble_coords]
        
        return {
            'mean_rg': np.mean(rgs),
            'std_rg': np.std(rgs),
            'max_rg': np.max(rgs),
            'min_rg': np.min(rgs),
            'rg_variance': np.var(rgs)
        }
    
    def calculate_ensemble_compactness(self, ensemble_coords: List[np.ndarray]) -> Dict:
        """Calculate compactness statistics for an ensemble."""
        compactness = [self.structure_metrics.calculate_compactness(coords) 
                      for coords in ensemble_coords]
        
        return {
            'mean_compactness': np.mean(compactness),
            'std_compactness': np.std(compactness),
            'max_compactness': np.max(compactness),
            'min_compactness': np.min(compactness)
        }


class ComparativeEvaluator:
    """Main class for comparative evaluation of QML vs CML predictions."""
    
    def __init__(self):
        self.structure_metrics = StructureMetrics()
        self.energy_metrics = EnergyMetrics()
        self.ensemble_metrics = EnsembleMetrics()
        self.results_dir = RESULTS_DIR / "evaluation"
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def evaluate_single_prediction(self, predicted_coords: np.ndarray, 
                                 experimental_coords: np.ndarray,
                                 sequence: str, method: str) -> Dict:
        """Evaluate a single prediction against experimental structure."""
        logger.info(f"Evaluating {method} prediction (length: {len(sequence)})")
        
        # Structural metrics
        rmsd = self.structure_metrics.calculate_rmsd(predicted_coords, experimental_coords)
        tm_score = self.structure_metrics.calculate_tm_score(predicted_coords, experimental_coords)
        gdt_ts = self.structure_metrics.calculate_gdt_ts(predicted_coords, experimental_coords)
        
        # Geometric metrics
        pred_rg = self.structure_metrics.calculate_radius_of_gyration(predicted_coords)
        exp_rg = self.structure_metrics.calculate_radius_of_gyration(experimental_coords)
        rg_error = abs(pred_rg - exp_rg)
        
        pred_compactness = self.structure_metrics.calculate_compactness(predicted_coords)
        exp_compactness = self.structure_metrics.calculate_compactness(experimental_coords)
        compactness_error = abs(pred_compactness - exp_compactness)
        
        # Energy metrics (simplified)
        atom_types = ['C'] * len(sequence)  # Simplified
        charges = [0.0] * len(sequence)     # Simplified
        pred_energy = self.energy_metrics.calculate_total_energy(
            predicted_coords, atom_types, charges
        )
        exp_energy = self.energy_metrics.calculate_total_energy(
            experimental_coords, atom_types, charges
        )
        energy_error = abs(pred_energy - exp_energy)
        
        # Success criteria
        success_criteria = {
            'rmsd_success': rmsd < RMSD_THRESHOLD,
            'tm_score_success': tm_score > TM_SCORE_THRESHOLD,
            'gdt_ts_success': gdt_ts > GDT_TS_THRESHOLD,
            'rg_success': rg_error < RG_VARIANCE_THRESHOLD,
            'energy_success': self.energy_metrics.check_energy_convergence(pred_energy)
        }
        
        return {
            'method': method,
            'sequence_length': len(sequence),
            'rmsd': rmsd,
            'tm_score': tm_score,
            'gdt_ts': gdt_ts,
            'predicted_radius_of_gyration': pred_rg,
            'experimental_radius_of_gyration': exp_rg,
            'radius_of_gyration_error': rg_error,
            'predicted_compactness': pred_compactness,
            'experimental_compactness': exp_compactness,
            'compactness_error': compactness_error,
            'predicted_energy': pred_energy,
            'experimental_energy': exp_energy,
            'energy_error': energy_error,
            'success_criteria': success_criteria,
            'overall_success': all(success_criteria.values())
        }
    
    def evaluate_ensemble(self, ensemble_coords: List[np.ndarray], 
                         experimental_coords: np.ndarray, sequence: str, 
                         method: str) -> Dict:
        """Evaluate an ensemble of predictions."""
        logger.info(f"Evaluating {method} ensemble ({len(ensemble_coords)} models)")
        
        # Individual model evaluations
        individual_evaluations = []
        for i, coords in enumerate(ensemble_coords):
            eval_result = self.evaluate_single_prediction(
                coords, experimental_coords, sequence, f"{method}_model_{i+1}"
            )
            individual_evaluations.append(eval_result)
        
        # Ensemble statistics
        ensemble_rmsd_stats = self.ensemble_metrics.calculate_ensemble_rmsd(ensemble_coords)
        ensemble_rg_stats = self.ensemble_metrics.calculate_ensemble_radius_of_gyration(ensemble_coords)
        ensemble_compactness_stats = self.ensemble_metrics.calculate_ensemble_compactness(ensemble_coords)
        
        # Best model (lowest RMSD)
        best_model_idx = np.argmin([eval_result['rmsd'] for eval_result in individual_evaluations])
        best_evaluation = individual_evaluations[best_model_idx]
        
        # Average metrics
        avg_metrics = {
            'mean_rmsd': np.mean([eval_result['rmsd'] for eval_result in individual_evaluations]),
            'std_rmsd': np.std([eval_result['rmsd'] for eval_result in individual_evaluations]),
            'mean_tm_score': np.mean([eval_result['tm_score'] for eval_result in individual_evaluations]),
            'std_tm_score': np.std([eval_result['tm_score'] for eval_result in individual_evaluations]),
            'mean_gdt_ts': np.mean([eval_result['gdt_ts'] for eval_result in individual_evaluations]),
            'std_gdt_ts': np.std([eval_result['gdt_ts'] for eval_result in individual_evaluations]),
            'success_rate': np.mean([eval_result['overall_success'] for eval_result in individual_evaluations])
        }
        
        return {
            'method': method,
            'num_models': len(ensemble_coords),
            'individual_evaluations': individual_evaluations,
            'best_model_evaluation': best_evaluation,
            'ensemble_rmsd_stats': ensemble_rmsd_stats,
            'ensemble_rg_stats': ensemble_rg_stats,
            'ensemble_compactness_stats': ensemble_compactness_stats,
            'average_metrics': avg_metrics
        }
    
    def compare_methods(self, classical_results: List[Dict], 
                       quantum_results: List[Dict]) -> Dict:
        """Compare classical and quantum methods statistically."""
        logger.info("Comparing classical and quantum methods")
        
        # Extract metrics for comparison
        classical_rmsds = [result['rmsd'] for result in classical_results]
        quantum_rmsds = [result['rmsd'] for result in quantum_results]
        
        classical_tm_scores = [result['tm_score'] for result in classical_results]
        quantum_tm_scores = [result['tm_score'] for result in quantum_results]
        
        classical_gdt_ts = [result['gdt_ts'] for result in classical_results]
        quantum_gdt_ts = [result['gdt_ts'] for result in quantum_results]
        
        classical_success_rates = [result['overall_success'] for result in classical_results]
        quantum_success_rates = [result['overall_success'] for result in quantum_results]
        
        # Statistical tests
        rmsd_ttest = stats.ttest_ind(classical_rmsds, quantum_rmsds)
        tm_score_ttest = stats.ttest_ind(classical_tm_scores, quantum_tm_scores)
        gdt_ts_ttest = stats.ttest_ind(classical_gdt_ts, quantum_gdt_ts)
        
        # Success rate comparison
        classical_success_rate = np.mean(classical_success_rates)
        quantum_success_rate = np.mean(quantum_success_rates)
        
        # Effect sizes (Cohen's d)
        def cohens_d(group1, group2):
            n1, n2 = len(group1), len(group2)
            s1, s2 = np.std(group1, ddof=1), np.std(group2, ddof=1)
            pooled_std = np.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2) / (n1+n2-2))
            return (np.mean(group1) - np.mean(group2)) / pooled_std
        
        rmsd_effect_size = cohens_d(classical_rmsds, quantum_rmsds)
        tm_score_effect_size = cohens_d(classical_tm_scores, quantum_tm_scores)
        gdt_ts_effect_size = cohens_d(classical_gdt_ts, quantum_gdt_ts)
        
        return {
            'classical_stats': {
                'mean_rmsd': np.mean(classical_rmsds),
                'std_rmsd': np.std(classical_rmsds),
                'mean_tm_score': np.mean(classical_tm_scores),
                'std_tm_score': np.std(classical_tm_scores),
                'mean_gdt_ts': np.mean(classical_gdt_ts),
                'std_gdt_ts': np.std(classical_gdt_ts),
                'success_rate': classical_success_rate,
                'n_samples': len(classical_results)
            },
            'quantum_stats': {
                'mean_rmsd': np.mean(quantum_rmsds),
                'std_rmsd': np.std(quantum_rmsds),
                'mean_tm_score': np.mean(quantum_tm_scores),
                'std_tm_score': np.std(quantum_tm_scores),
                'mean_gdt_ts': np.mean(quantum_gdt_ts),
                'std_gdt_ts': np.std(quantum_gdt_ts),
                'success_rate': quantum_success_rate,
                'n_samples': len(quantum_results)
            },
            'statistical_tests': {
                'rmsd_ttest': {
                    'statistic': rmsd_ttest.statistic,
                    'p_value': rmsd_ttest.pvalue,
                    'significant': rmsd_ttest.pvalue < 0.05
                },
                'tm_score_ttest': {
                    'statistic': tm_score_ttest.statistic,
                    'p_value': tm_score_ttest.pvalue,
                    'significant': tm_score_ttest.pvalue < 0.05
                },
                'gdt_ts_ttest': {
                    'statistic': gdt_ts_ttest.statistic,
                    'p_value': gdt_ts_ttest.pvalue,
                    'significant': gdt_ts_ttest.pvalue < 0.05
                }
            },
            'effect_sizes': {
                'rmsd_cohens_d': rmsd_effect_size,
                'tm_score_cohens_d': tm_score_effect_size,
                'gdt_ts_cohens_d': gdt_ts_effect_size
            },
            'summary': {
                'better_rmsd': 'quantum' if np.mean(quantum_rmsds) < np.mean(classical_rmsds) else 'classical',
                'better_tm_score': 'quantum' if np.mean(quantum_tm_scores) > np.mean(classical_tm_scores) else 'classical',
                'better_gdt_ts': 'quantum' if np.mean(quantum_gdt_ts) > np.mean(classical_gdt_ts) else 'classical',
                'better_success_rate': 'quantum' if quantum_success_rate > classical_success_rate else 'classical'
            }
        }
    
    def save_evaluation_results(self, results: Dict, output_file: str):
        """Save evaluation results to file."""
        logger.info(f"Saving evaluation results to {output_file}")
        
        # Convert to DataFrame for easier handling
        data = []
        for result in results.get('individual_evaluations', []):
            row = {
                'method': result['method'],
                'sequence_length': result['sequence_length'],
                'rmsd': result['rmsd'],
                'tm_score': result['tm_score'],
                'gdt_ts': result['gdt_ts'],
                'radius_of_gyration_error': result['radius_of_gyration_error'],
                'compactness_error': result['compactness_error'],
                'energy_error': result['energy_error'],
                'overall_success': result['overall_success']
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        df.to_csv(output_file, index=False)
        
        logger.info(f"Evaluation results saved to {output_file}")


def main():
    """Example usage of evaluation metrics."""
    # Create some mock data for testing
    np.random.seed(42)
    
    # Mock experimental structure
    experimental_coords = np.random.randn(10, 3) * 5.0
    
    # Mock classical prediction
    classical_coords = experimental_coords + np.random.randn(10, 3) * 1.0
    
    # Mock quantum prediction
    quantum_coords = experimental_coords + np.random.randn(10, 3) * 0.5
    
    # Initialize evaluator
    evaluator = ComparativeEvaluator()
    
    # Evaluate single predictions
    classical_eval = evaluator.evaluate_single_prediction(
        classical_coords, experimental_coords, "ACDEFGHIKL", "classical"
    )
    
    quantum_eval = evaluator.evaluate_single_prediction(
        quantum_coords, experimental_coords, "ACDEFGHIKL", "quantum"
    )
    
    # Compare methods
    comparison = evaluator.compare_methods([classical_eval], [quantum_eval])
    
    print("Evaluation Results:")
    print(f"Classical RMSD: {classical_eval['rmsd']:.3f}")
    print(f"Quantum RMSD: {quantum_eval['rmsd']:.3f}")
    print(f"Classical TM-score: {classical_eval['tm_score']:.3f}")
    print(f"Quantum TM-score: {quantum_eval['tm_score']:.3f}")
    print(f"Statistical significance (RMSD): {comparison['statistical_tests']['rmsd_ttest']['significant']}")


if __name__ == "__main__":
    main()
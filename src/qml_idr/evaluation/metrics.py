"""Evaluation metrics for comparing QML and CML IDR predictions."""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
from Bio.PDB import PDBParser, Superimposer
from Bio.PDB.vectors import calc_dihedral
from scipy import stats
from sklearn.metrics import mean_squared_error, mean_absolute_error
import mdtraj as md

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class StructuralMetrics:
    """Structural metrics for protein conformation evaluation."""
    
    def __init__(self):
        """Initialize structural metrics calculator."""
        self.config = get_config()
        self.parser = PDBParser(QUIET=True)
        self.superimposer = Superimposer()
    
    def calculate_rmsd(self, structure1: Union[Path, np.ndarray], 
                      structure2: Union[Path, np.ndarray],
                      atom_type: str = 'CA') -> float:
        """Calculate RMSD between two structures.
        
        Args:
            structure1: First structure (PDB file or coordinates)
            structure2: Second structure (PDB file or coordinates)
            atom_type: Atom type for RMSD calculation ('CA', 'backbone', 'all')
            
        Returns:
            RMSD value in Angstroms
        """
        coords1 = self._extract_coordinates(structure1, atom_type)
        coords2 = self._extract_coordinates(structure2, atom_type)
        
        if coords1 is None or coords2 is None:
            return float('inf')
        
        if coords1.shape != coords2.shape:
            logger.warning(f"Coordinate shape mismatch: {coords1.shape} vs {coords2.shape}")
            # Truncate to smaller size
            min_size = min(len(coords1), len(coords2))
            coords1 = coords1[:min_size]
            coords2 = coords2[:min_size]
        
        # Superimpose and calculate RMSD
        try:
            self.superimposer.set_atoms(
                [self._coord_to_atom(coord, i) for i, coord in enumerate(coords1)],
                [self._coord_to_atom(coord, i) for i, coord in enumerate(coords2)]
            )
            rmsd = self.superimposer.rms
            return float(rmsd)
        
        except Exception as e:
            logger.error(f"RMSD calculation failed: {e}")
            # Fallback to simple Euclidean distance
            return float(np.sqrt(np.mean((coords1 - coords2)**2)))
    
    def calculate_gdt_ts(self, structure1: Union[Path, np.ndarray],
                        structure2: Union[Path, np.ndarray],
                        cutoffs: List[float] = None) -> float:
        """Calculate GDT_TS score.
        
        Args:
            structure1: Predicted structure
            structure2: Reference structure
            cutoffs: Distance cutoffs (default: [1, 2, 4, 8] Angstroms)
            
        Returns:
            GDT_TS score (0-100)
        """
        if cutoffs is None:
            cutoffs = [1.0, 2.0, 4.0, 8.0]
        
        coords1 = self._extract_coordinates(structure1, 'CA')
        coords2 = self._extract_coordinates(structure2, 'CA')
        
        if coords1 is None or coords2 is None:
            return 0.0
        
        min_size = min(len(coords1), len(coords2))
        coords1 = coords1[:min_size]
        coords2 = coords2[:min_size]
        
        # Calculate distances after optimal superposition
        try:
            self.superimposer.set_atoms(
                [self._coord_to_atom(coord, i) for i, coord in enumerate(coords1)],
                [self._coord_to_atom(coord, i) for i, coord in enumerate(coords2)]
            )
            
            # Apply transformation to coords1
            rotation, translation = self.superimposer.rotran
            aligned_coords1 = np.array([np.dot(coord, rotation) + translation for coord in coords1])
            
            # Calculate distances
            distances = np.linalg.norm(aligned_coords1 - coords2, axis=1)
            
            # Calculate GDT_TS
            gdt_scores = []
            for cutoff in cutoffs:
                fraction_within_cutoff = np.sum(distances <= cutoff) / len(distances)
                gdt_scores.append(fraction_within_cutoff)
            
            gdt_ts = np.mean(gdt_scores) * 100  # Convert to percentage
            return float(gdt_ts)
        
        except Exception as e:
            logger.error(f"GDT_TS calculation failed: {e}")
            return 0.0
    
    def calculate_tm_score(self, structure1: Union[Path, np.ndarray],
                          structure2: Union[Path, np.ndarray]) -> float:
        """Calculate TM-score.
        
        Args:
            structure1: Predicted structure
            structure2: Reference structure
            
        Returns:
            TM-score (0-1)
        """
        coords1 = self._extract_coordinates(structure1, 'CA')
        coords2 = self._extract_coordinates(structure2, 'CA')
        
        if coords1 is None or coords2 is None:
            return 0.0
        
        min_size = min(len(coords1), len(coords2))
        coords1 = coords1[:min_size]
        coords2 = coords2[:min_size]
        
        L_target = len(coords2)  # Length of target (reference) structure
        d0 = 1.24 * (L_target - 15)**(1/3) - 1.8  # TM-score normalization
        d0 = max(d0, 0.5)  # Minimum d0
        
        try:
            # Find optimal superposition
            self.superimposer.set_atoms(
                [self._coord_to_atom(coord, i) for i, coord in enumerate(coords1)],
                [self._coord_to_atom(coord, i) for i, coord in enumerate(coords2)]
            )
            
            # Apply transformation
            rotation, translation = self.superimposer.rotran
            aligned_coords1 = np.array([np.dot(coord, rotation) + translation for coord in coords1])
            
            # Calculate TM-score
            distances = np.linalg.norm(aligned_coords1 - coords2, axis=1)
            tm_score = np.sum(1 / (1 + (distances / d0)**2)) / L_target
            
            return float(tm_score)
        
        except Exception as e:
            logger.error(f"TM-score calculation failed: {e}")
            return 0.0
    
    def calculate_radius_of_gyration(self, structure: Union[Path, np.ndarray]) -> float:
        """Calculate radius of gyration.
        
        Args:
            structure: Structure (PDB file or coordinates)
            
        Returns:
            Radius of gyration in Angstroms
        """
        coords = self._extract_coordinates(structure, 'CA')
        
        if coords is None:
            return 0.0
        
        # Calculate center of mass
        center_of_mass = np.mean(coords, axis=0)
        
        # Calculate Rg
        distances_to_com = np.linalg.norm(coords - center_of_mass, axis=1)
        rg = np.sqrt(np.mean(distances_to_com**2))
        
        return float(rg)
    
    def calculate_end_to_end_distance(self, structure: Union[Path, np.ndarray]) -> float:
        """Calculate end-to-end distance.
        
        Args:
            structure: Structure (PDB file or coordinates)
            
        Returns:
            End-to-end distance in Angstroms
        """
        coords = self._extract_coordinates(structure, 'CA')
        
        if coords is None or len(coords) < 2:
            return 0.0
        
        end_to_end = np.linalg.norm(coords[-1] - coords[0])
        return float(end_to_end)
    
    def calculate_dihedral_rmsd(self, structure1: Union[Path, np.ndarray],
                              structure2: Union[Path, np.ndarray]) -> float:
        """Calculate RMSD of dihedral angles.
        
        Args:
            structure1: First structure
            structure2: Second structure
            
        Returns:
            Dihedral RMSD in degrees
        """
        angles1 = self._extract_dihedral_angles(structure1)
        angles2 = self._extract_dihedral_angles(structure2)
        
        if angles1 is None or angles2 is None:
            return float('inf')
        
        min_size = min(len(angles1), len(angles2))
        angles1 = angles1[:min_size]
        angles2 = angles2[:min_size]
        
        # Calculate circular difference
        diff = angles1 - angles2
        diff = np.arctan2(np.sin(diff), np.cos(diff))  # Wrap to [-π, π]
        
        rmsd = np.sqrt(np.mean(diff**2)) * 180 / np.pi  # Convert to degrees
        return float(rmsd)
    
    def _extract_coordinates(self, structure: Union[Path, np.ndarray], 
                           atom_type: str) -> Optional[np.ndarray]:
        """Extract coordinates from structure.
        
        Args:
            structure: Structure (PDB file or coordinates array)
            atom_type: Type of atoms to extract
            
        Returns:
            Coordinates array or None if failed
        """
        if isinstance(structure, np.ndarray):
            if atom_type == 'CA' and structure.shape[1] >= 2:
                return structure[:, 1, :]  # CA is usually index 1
            elif atom_type == 'backbone':
                return structure[:, :4, :].reshape(-1, 3)  # N, CA, C, O
            else:
                return structure.reshape(-1, 3)
        
        elif isinstance(structure, (str, Path)):
            try:
                pdb_structure = self.parser.get_structure('protein', structure)
                coords = []
                
                for model in pdb_structure:
                    for chain in model:
                        for residue in chain:
                            if residue.get_id()[0] == ' ':  # Standard residue
                                if atom_type == 'CA':
                                    if 'CA' in residue:
                                        coords.append(residue['CA'].get_coord())
                                elif atom_type == 'backbone':
                                    for atom_name in ['N', 'CA', 'C', 'O']:
                                        if atom_name in residue:
                                            coords.append(residue[atom_name].get_coord())
                                else:  # all atoms
                                    for atom in residue:
                                        coords.append(atom.get_coord())
                
                return np.array(coords) if coords else None
            
            except Exception as e:
                logger.error(f"Failed to extract coordinates from {structure}: {e}")
                return None
        
        return None
    
    def _extract_dihedral_angles(self, structure: Union[Path, np.ndarray]) -> Optional[np.ndarray]:
        """Extract phi/psi dihedral angles.
        
        Args:
            structure: Structure (PDB file or coordinates)
            
        Returns:
            Array of [phi, psi] angles or None
        """
        if isinstance(structure, np.ndarray):
            # Assume structure is [N_residues, 4, 3] for N, CA, C, O
            if structure.shape[1] < 4:
                return None
            
            angles = []
            for i in range(1, len(structure) - 1):
                try:
                    # Phi: C(i-1) - N(i) - CA(i) - C(i)
                    phi = calc_dihedral(
                        structure[i-1, 2], structure[i, 0],
                        structure[i, 1], structure[i, 2]
                    )
                    
                    # Psi: N(i) - CA(i) - C(i) - N(i+1)
                    psi = calc_dihedral(
                        structure[i, 0], structure[i, 1],
                        structure[i, 2], structure[i+1, 0]
                    )
                    
                    angles.append([phi, psi])
                
                except Exception:
                    angles.append([0.0, 0.0])
            
            return np.array(angles) if angles else None
        
        elif isinstance(structure, (str, Path)):
            try:
                pdb_structure = self.parser.get_structure('protein', structure)
                angles = []
                
                residues = []
                for model in pdb_structure:
                    for chain in model:
                        for residue in chain:
                            if residue.get_id()[0] == ' ':
                                residues.append(residue)
                
                for i in range(1, len(residues) - 1):
                    try:
                        # Get atoms for dihedral calculation
                        prev_c = residues[i-1]['C']
                        curr_n = residues[i]['N']
                        curr_ca = residues[i]['CA']
                        curr_c = residues[i]['C']
                        next_n = residues[i+1]['N']
                        
                        phi = calc_dihedral(
                            prev_c.get_vector(), curr_n.get_vector(),
                            curr_ca.get_vector(), curr_c.get_vector()
                        )
                        
                        psi = calc_dihedral(
                            curr_n.get_vector(), curr_ca.get_vector(),
                            curr_c.get_vector(), next_n.get_vector()
                        )
                        
                        angles.append([phi, psi])
                    
                    except KeyError:
                        angles.append([0.0, 0.0])
                
                return np.array(angles) if angles else None
            
            except Exception as e:
                logger.error(f"Failed to extract dihedral angles from {structure}: {e}")
                return None
        
        return None
    
    def _coord_to_atom(self, coord: np.ndarray, serial: int):
        """Convert coordinate to PDB Atom object."""
        from Bio.PDB import Atom
        return Atom.Atom('CA', coord, 1.0, 1.0, ' ', 'CA', serial, element='C')
    
    def calculate_ensemble_metrics(self, structures: List[Path]) -> Dict:
        """Calculate metrics for ensemble of structures.
        
        Args:
            structures: List of structure files
            
        Returns:
            Dictionary with ensemble metrics
        """
        if len(structures) < 2:
            return {}
        
        # Calculate pairwise RMSDs
        pairwise_rmsds = []
        for i in range(len(structures)):
            for j in range(i + 1, len(structures)):
                rmsd = self.calculate_rmsd(structures[i], structures[j])
                pairwise_rmsds.append(rmsd)
        
        # Calculate radius of gyration for each structure
        rg_values = [self.calculate_radius_of_gyration(struct) for struct in structures]
        
        # Calculate end-to-end distances
        e2e_values = [self.calculate_end_to_end_distance(struct) for struct in structures]
        
        ensemble_metrics = {
            'ensemble_size': len(structures),
            'mean_pairwise_rmsd': np.mean(pairwise_rmsds),
            'std_pairwise_rmsd': np.std(pairwise_rmsds),
            'min_pairwise_rmsd': np.min(pairwise_rmsds),
            'max_pairwise_rmsd': np.max(pairwise_rmsds),
            'mean_rg': np.mean(rg_values),
            'std_rg': np.std(rg_values),
            'mean_e2e': np.mean(e2e_values),
            'std_e2e': np.std(e2e_values),
            'rg_coefficient_of_variation': np.std(rg_values) / np.mean(rg_values) if np.mean(rg_values) > 0 else 0,
            'e2e_coefficient_of_variation': np.std(e2e_values) / np.mean(e2e_values) if np.mean(e2e_values) > 0 else 0
        }
        
        return ensemble_metrics
    
    def calculate_structural_metrics(self, predicted: Path, reference: Path) -> Dict:
        """Calculate comprehensive structural metrics.
        
        Args:
            predicted: Predicted structure file
            reference: Reference structure file
            
        Returns:
            Dictionary with all structural metrics
        """
        metrics = {}
        
        try:
            # RMSD metrics
            metrics['ca_rmsd'] = self.calculate_rmsd(predicted, reference, 'CA')
            metrics['backbone_rmsd'] = self.calculate_rmsd(predicted, reference, 'backbone')
            
            # Global fold metrics
            metrics['gdt_ts'] = self.calculate_gdt_ts(predicted, reference)
            metrics['tm_score'] = self.calculate_tm_score(predicted, reference)
            
            # Structural properties
            pred_rg = self.calculate_radius_of_gyration(predicted)
            ref_rg = self.calculate_radius_of_gyration(reference)
            metrics['predicted_rg'] = pred_rg
            metrics['reference_rg'] = ref_rg
            metrics['rg_difference'] = abs(pred_rg - ref_rg)
            
            pred_e2e = self.calculate_end_to_end_distance(predicted)
            ref_e2e = self.calculate_end_to_end_distance(reference)
            metrics['predicted_e2e'] = pred_e2e
            metrics['reference_e2e'] = ref_e2e
            metrics['e2e_difference'] = abs(pred_e2e - ref_e2e)
            
            # Dihedral angles
            metrics['dihedral_rmsd'] = self.calculate_dihedral_rmsd(predicted, reference)
            
        except Exception as e:
            logger.error(f"Error calculating structural metrics: {e}")
            # Return default values
            for key in ['ca_rmsd', 'backbone_rmsd', 'gdt_ts', 'tm_score',
                       'predicted_rg', 'reference_rg', 'rg_difference',
                       'predicted_e2e', 'reference_e2e', 'e2e_difference',
                       'dihedral_rmsd']:
                metrics[key] = 0.0
        
        return metrics


class EnergyMetrics:
    """Energy-based evaluation metrics."""
    
    def __init__(self):
        """Initialize energy metrics calculator."""
        self.config = get_config()
    
    def calculate_potential_energy(self, coordinates: np.ndarray, 
                                 sequence: str, 
                                 force_field: str = 'amber') -> Dict[str, float]:
        """Calculate potential energy using molecular mechanics.
        
        Args:
            coordinates: Protein coordinates
            sequence: Protein sequence
            force_field: Force field to use
            
        Returns:
            Dictionary with energy components
        """
        try:
            # This is a simplified energy calculation
            # In practice, you would use OpenMM or similar
            
            from ..data.preprocessor import ProteinPreprocessor
            preprocessor = ProteinPreprocessor()
            
            energy_features = preprocessor.calculate_energy_features(coordinates, sequence)
            
            # Add total potential energy estimate
            total_energy = sum(energy_features.values())
            
            energy_metrics = {
                'total_potential_energy': total_energy,
                'vdw_energy': energy_features.get('vdw_energy', 0.0),
                'electrostatic_energy': energy_features.get('electrostatic_energy', 0.0),
                'solvation_energy': energy_features.get('solvation_energy', 0.0),
                'energy_per_residue': total_energy / len(sequence) if sequence else 0.0
            }
            
            return energy_metrics
        
        except Exception as e:
            logger.error(f"Energy calculation failed: {e}")
            return {
                'total_potential_energy': 0.0,
                'vdw_energy': 0.0,
                'electrostatic_energy': 0.0,
                'solvation_energy': 0.0,
                'energy_per_residue': 0.0
            }
    
    def calculate_energy_minimization_success(self, initial_coords: np.ndarray,
                                            final_coords: np.ndarray,
                                            sequence: str,
                                            energy_threshold: float = None) -> Dict:
        """Evaluate energy minimization success.
        
        Args:
            initial_coords: Initial coordinates
            final_coords: Final coordinates after minimization
            sequence: Protein sequence
            energy_threshold: Energy threshold for success
            
        Returns:
            Dictionary with minimization metrics
        """
        if energy_threshold is None:
            energy_threshold = self.config.evaluation.metrics.energy_threshold
        
        # Calculate energies
        initial_energy = self.calculate_potential_energy(initial_coords, sequence)
        final_energy = self.calculate_potential_energy(final_coords, sequence)
        
        energy_change = final_energy['total_potential_energy'] - initial_energy['total_potential_energy']
        
        minimization_metrics = {
            'initial_energy': initial_energy['total_potential_energy'],
            'final_energy': final_energy['total_potential_energy'],
            'energy_change': energy_change,
            'energy_improvement': energy_change < 0,
            'meets_threshold': final_energy['total_potential_energy'] < energy_threshold,
            'convergence_ratio': abs(energy_change) / abs(initial_energy['total_potential_energy']) if initial_energy['total_potential_energy'] != 0 else 0,
            'structural_rmsd': np.sqrt(np.mean((initial_coords - final_coords)**2))
        }
        
        return minimization_metrics


class ComparativeAnalysis:
    """Comparative analysis between QML and CML methods."""
    
    def __init__(self):
        """Initialize comparative analysis."""
        self.config = get_config()
        self.structural_metrics = StructuralMetrics()
        self.energy_metrics = EnergyMetrics()
    
    def compare_methods(self, qml_results: List[Dict], 
                       cml_results: List[Dict],
                       reference_structures: List[Path] = None) -> Dict:
        """Compare QML and CML results.
        
        Args:
            qml_results: List of QML prediction results
            cml_results: List of CML prediction results
            reference_structures: List of reference structures (optional)
            
        Returns:
            Dictionary with comparative analysis results
        """
        logger.info("Performing comparative analysis between QML and CML methods")
        
        comparison_results = {
            'qml_metrics': self._analyze_method_results(qml_results, 'QML', reference_structures),
            'cml_metrics': self._analyze_method_results(cml_results, 'CML', reference_structures),
            'statistical_comparison': {},
            'performance_summary': {}
        }
        
        # Statistical comparison
        if qml_results and cml_results:
            comparison_results['statistical_comparison'] = self._statistical_comparison(
                qml_results, cml_results, reference_structures
            )
        
        # Performance summary
        comparison_results['performance_summary'] = self._create_performance_summary(
            comparison_results['qml_metrics'],
            comparison_results['cml_metrics']
        )
        
        return comparison_results
    
    def _analyze_method_results(self, results: List[Dict], 
                              method_name: str,
                              reference_structures: List[Path] = None) -> Dict:
        """Analyze results for a single method.
        
        Args:
            results: List of prediction results
            method_name: Name of the method
            reference_structures: Reference structures for comparison
            
        Returns:
            Dictionary with method analysis
        """
        if not results:
            return {}
        
        logger.info(f"Analyzing {len(results)} {method_name} results")
        
        analysis = {
            'n_predictions': len(results),
            'successful_predictions': 0,
            'runtime_stats': {},
            'energy_stats': {},
            'structural_stats': {},
            'convergence_stats': {}
        }
        
        # Collect metrics
        runtimes = []
        energies = []
        structural_metrics_list = []
        convergence_rates = []
        
        for i, result in enumerate(results):
            # Runtime
            if 'runtime' in result:
                runtimes.append(result['runtime'])
            
            # Energy
            if 'ground_state_energy' in result:
                energies.append(result['ground_state_energy'])
            
            # Convergence
            if 'converged' in result:
                convergence_rates.append(1 if result['converged'] else 0)
                if result['converged']:
                    analysis['successful_predictions'] += 1
            
            # Structural metrics (if reference available)
            if reference_structures and i < len(reference_structures):
                if 'predicted_coordinates' in result:
                    # Create temporary PDB for comparison
                    temp_structure = self._create_temp_structure(
                        result['predicted_coordinates'],
                        result.get('sequence', 'A' * len(result['predicted_coordinates']))
                    )
                    
                    if temp_structure:
                        metrics = self.structural_metrics.calculate_structural_metrics(
                            temp_structure, reference_structures[i]
                        )
                        structural_metrics_list.append(metrics)
        
        # Calculate statistics
        if runtimes:
            analysis['runtime_stats'] = {
                'mean': np.mean(runtimes),
                'std': np.std(runtimes),
                'median': np.median(runtimes),
                'min': np.min(runtimes),
                'max': np.max(runtimes)
            }
        
        if energies:
            analysis['energy_stats'] = {
                'mean': np.mean(energies),
                'std': np.std(energies),
                'median': np.median(energies),
                'min': np.min(energies),
                'max': np.max(energies)
            }
        
        if convergence_rates:
            analysis['convergence_stats'] = {
                'success_rate': np.mean(convergence_rates),
                'total_attempts': len(convergence_rates),
                'successful_runs': sum(convergence_rates)
            }
        
        if structural_metrics_list:
            # Aggregate structural metrics
            structural_stats = {}
            for key in structural_metrics_list[0].keys():
                values = [m[key] for m in structural_metrics_list if key in m and not np.isnan(m[key])]
                if values:
                    structural_stats[key] = {
                        'mean': np.mean(values),
                        'std': np.std(values),
                        'median': np.median(values),
                        'min': np.min(values),
                        'max': np.max(values)
                    }
            
            analysis['structural_stats'] = structural_stats
        
        return analysis
    
    def _statistical_comparison(self, qml_results: List[Dict], 
                              cml_results: List[Dict],
                              reference_structures: List[Path] = None) -> Dict:
        """Perform statistical comparison between methods.
        
        Args:
            qml_results: QML results
            cml_results: CML results
            reference_structures: Reference structures
            
        Returns:
            Dictionary with statistical test results
        """
        statistical_tests = {}
        
        # Compare runtimes
        qml_runtimes = [r.get('runtime', 0) for r in qml_results if 'runtime' in r]
        cml_runtimes = [r.get('runtime', 0) for r in cml_results if 'runtime' in r]
        
        if qml_runtimes and cml_runtimes:
            statistic, p_value = stats.mannwhitneyu(qml_runtimes, cml_runtimes, alternative='two-sided')
            statistical_tests['runtime_comparison'] = {
                'test': 'Mann-Whitney U',
                'statistic': float(statistic),
                'p_value': float(p_value),
                'significant': p_value < self.config.evaluation.validation.statistical_significance,
                'qml_median': np.median(qml_runtimes),
                'cml_median': np.median(cml_runtimes)
            }
        
        # Compare energies
        qml_energies = [r.get('ground_state_energy', 0) for r in qml_results if 'ground_state_energy' in r and np.isfinite(r['ground_state_energy'])]
        cml_energies = [r.get('total_potential_energy', 0) for r in cml_results if 'total_potential_energy' in r]
        
        if qml_energies and cml_energies:
            try:
                statistic, p_value = stats.mannwhitneyu(qml_energies, cml_energies, alternative='two-sided')
                statistical_tests['energy_comparison'] = {
                    'test': 'Mann-Whitney U',
                    'statistic': float(statistic),
                    'p_value': float(p_value),
                    'significant': p_value < self.config.evaluation.validation.statistical_significance,
                    'qml_median': np.median(qml_energies),
                    'cml_median': np.median(cml_energies)
                }
            except ValueError as e:
                logger.warning(f"Energy comparison failed: {e}")
        
        # Compare convergence rates
        qml_convergence = [1 if r.get('converged', False) else 0 for r in qml_results]
        cml_convergence = [1 if r.get('converged', True) else 0 for r in cml_results]  # CML typically converges
        
        if qml_convergence and cml_convergence:
            # Chi-square test for proportions
            from scipy.stats import chi2_contingency
            
            contingency_table = np.array([
                [sum(qml_convergence), len(qml_convergence) - sum(qml_convergence)],
                [sum(cml_convergence), len(cml_convergence) - sum(cml_convergence)]
            ])
            
            if np.all(contingency_table >= 5):  # Chi-square assumption
                chi2, p_value, _, _ = chi2_contingency(contingency_table)
                statistical_tests['convergence_comparison'] = {
                    'test': 'Chi-square',
                    'statistic': float(chi2),
                    'p_value': float(p_value),
                    'significant': p_value < self.config.evaluation.validation.statistical_significance,
                    'qml_success_rate': np.mean(qml_convergence),
                    'cml_success_rate': np.mean(cml_convergence)
                }
        
        return statistical_tests
    
    def _create_performance_summary(self, qml_metrics: Dict, cml_metrics: Dict) -> Dict:
        """Create performance summary.
        
        Args:
            qml_metrics: QML analysis results
            cml_metrics: CML analysis results
            
        Returns:
            Performance summary dictionary
        """
        summary = {
            'winner_by_metric': {},
            'overall_assessment': {},
            'recommendations': []
        }
        
        # Compare key metrics
        metrics_to_compare = [
            ('runtime', 'runtime_stats', 'mean', 'lower_better'),
            ('energy', 'energy_stats', 'mean', 'lower_better'),
            ('convergence', 'convergence_stats', 'success_rate', 'higher_better'),
            ('ca_rmsd', 'structural_stats', 'mean', 'lower_better'),
            ('tm_score', 'structural_stats', 'mean', 'higher_better')
        ]
        
        for metric_name, stats_key, value_key, direction in metrics_to_compare:
            qml_value = qml_metrics.get(stats_key, {}).get(value_key)
            cml_value = cml_metrics.get(stats_key, {}).get(value_key)
            
            if qml_value is not None and cml_value is not None:
                if direction == 'lower_better':
                    winner = 'QML' if qml_value < cml_value else 'CML'
                    improvement = abs(qml_value - cml_value) / cml_value * 100
                else:
                    winner = 'QML' if qml_value > cml_value else 'CML'
                    improvement = abs(qml_value - cml_value) / cml_value * 100
                
                summary['winner_by_metric'][metric_name] = {
                    'winner': winner,
                    'qml_value': qml_value,
                    'cml_value': cml_value,
                    'improvement_percent': improvement
                }
        
        # Overall assessment
        qml_wins = sum(1 for result in summary['winner_by_metric'].values() if result['winner'] == 'QML')
        cml_wins = sum(1 for result in summary['winner_by_metric'].values() if result['winner'] == 'CML')
        
        summary['overall_assessment'] = {
            'qml_wins': qml_wins,
            'cml_wins': cml_wins,
            'total_comparisons': len(summary['winner_by_metric']),
            'overall_winner': 'QML' if qml_wins > cml_wins else 'CML' if cml_wins > qml_wins else 'Tie'
        }
        
        # Generate recommendations
        if qml_wins > cml_wins:
            summary['recommendations'].append(
                "QML shows superior performance in the majority of metrics. "
                "Consider QML for high-accuracy IDR predictions where computational resources allow."
            )
        elif cml_wins > qml_wins:
            summary['recommendations'].append(
                "CML (AlphaFold3) shows superior performance in the majority of metrics. "
                "CML is recommended for routine IDR analysis and large-scale studies."
            )
        else:
            summary['recommendations'].append(
                "QML and CML show comparable performance. "
                "Method choice should depend on specific requirements and available resources."
            )
        
        # Add specific recommendations based on metrics
        runtime_comparison = summary['winner_by_metric'].get('runtime')
        if runtime_comparison and runtime_comparison['improvement_percent'] > 50:
            faster_method = runtime_comparison['winner']
            summary['recommendations'].append(
                f"{faster_method} is significantly faster ({runtime_comparison['improvement_percent']:.1f}% improvement). "
                f"Consider {faster_method} for time-critical applications."
            )
        
        return summary
    
    def _create_temp_structure(self, coordinates: np.ndarray, sequence: str) -> Optional[Path]:
        """Create temporary PDB structure from coordinates.
        
        Args:
            coordinates: Coordinates array
            sequence: Protein sequence
            
        Returns:
            Path to temporary PDB file or None
        """
        try:
            import tempfile
            from Bio.PDB import PDBIO, Structure, Model, Chain, Residue, Atom
            
            # Create structure
            structure = Structure.Structure('temp')
            model = Model.Model(0)
            structure.add(model)
            
            chain = Chain.Chain('A')
            model.add(chain)
            
            atom_names = ['N', 'CA', 'C', 'O']
            
            for i, aa in enumerate(sequence[:len(coordinates)]):
                residue = Residue.Residue((' ', i + 1, ' '), aa, ' ')
                chain.add(residue)
                
                for j, atom_name in enumerate(atom_names):
                    if j < coordinates.shape[1]:
                        atom = Atom.Atom(
                            atom_name,
                            coordinates[i, j],
                            1.0, 1.0, ' ', atom_name, j + 1,
                            element=atom_name[0]
                        )
                        residue.add(atom)
            
            # Save to temporary file
            temp_file = Path(tempfile.mktemp(suffix='.pdb'))
            io = PDBIO()
            io.set_structure(structure)
            io.save(str(temp_file))
            
            return temp_file
        
        except Exception as e:
            logger.error(f"Failed to create temporary structure: {e}")
            return None
    
    def generate_report(self, comparison_results: Dict, output_file: Path):
        """Generate comprehensive comparison report.
        
        Args:
            comparison_results: Results from compare_methods
            output_file: Output file path
        """
        logger.info(f"Generating comparison report: {output_file}")
        
        with open(output_file, 'w') as f:
            f.write("# QML vs CML IDR Prediction Comparison Report\n\n")
            
            # Executive Summary
            f.write("## Executive Summary\n\n")
            summary = comparison_results.get('performance_summary', {})
            overall = summary.get('overall_assessment', {})
            
            f.write(f"- **Overall Winner**: {overall.get('overall_winner', 'Unknown')}\n")
            f.write(f"- **QML Wins**: {overall.get('qml_wins', 0)} metrics\n")
            f.write(f"- **CML Wins**: {overall.get('cml_wins', 0)} metrics\n")
            f.write(f"- **Total Comparisons**: {overall.get('total_comparisons', 0)}\n\n")
            
            # Recommendations
            recommendations = summary.get('recommendations', [])
            if recommendations:
                f.write("### Recommendations\n\n")
                for i, rec in enumerate(recommendations, 1):
                    f.write(f"{i}. {rec}\n\n")
            
            # Detailed Results
            f.write("## Detailed Results\n\n")
            
            # QML Results
            f.write("### Quantum Machine Learning (QML) Results\n\n")
            qml_metrics = comparison_results.get('qml_metrics', {})
            self._write_method_results(f, qml_metrics)
            
            # CML Results
            f.write("### Classical Machine Learning (CML) Results\n\n")
            cml_metrics = comparison_results.get('cml_metrics', {})
            self._write_method_results(f, cml_metrics)
            
            # Statistical Comparison
            f.write("### Statistical Comparison\n\n")
            statistical_tests = comparison_results.get('statistical_comparison', {})
            
            for test_name, test_results in statistical_tests.items():
                f.write(f"#### {test_name.replace('_', ' ').title()}\n\n")
                f.write(f"- **Test**: {test_results.get('test', 'Unknown')}\n")
                f.write(f"- **P-value**: {test_results.get('p_value', 'N/A'):.6f}\n")
                f.write(f"- **Significant**: {'Yes' if test_results.get('significant', False) else 'No'}\n")
                
                if 'qml_median' in test_results:
                    f.write(f"- **QML Median**: {test_results['qml_median']:.4f}\n")
                    f.write(f"- **CML Median**: {test_results['cml_median']:.4f}\n")
                
                f.write("\n")
            
            # Performance by Metric
            f.write("### Performance by Metric\n\n")
            winner_by_metric = summary.get('winner_by_metric', {})
            
            f.write("| Metric | Winner | QML Value | CML Value | Improvement (%) |\n")
            f.write("|--------|---------|-----------|-----------|------------------|\n")
            
            for metric, results in winner_by_metric.items():
                f.write(f"| {metric} | {results['winner']} | {results['qml_value']:.4f} | "
                       f"{results['cml_value']:.4f} | {results['improvement_percent']:.1f} |\n")
            
            f.write("\n")
        
        logger.info(f"Comparison report saved to {output_file}")
    
    def _write_method_results(self, f, metrics: Dict):
        """Write method results to file.
        
        Args:
            f: File handle
            metrics: Method metrics dictionary
        """
        f.write(f"- **Total Predictions**: {metrics.get('n_predictions', 0)}\n")
        f.write(f"- **Successful Predictions**: {metrics.get('successful_predictions', 0)}\n")
        
        # Runtime stats
        runtime_stats = metrics.get('runtime_stats', {})
        if runtime_stats:
            f.write(f"- **Mean Runtime**: {runtime_stats.get('mean', 0):.2f} seconds\n")
            f.write(f"- **Runtime Std**: {runtime_stats.get('std', 0):.2f} seconds\n")
        
        # Energy stats
        energy_stats = metrics.get('energy_stats', {})
        if energy_stats:
            f.write(f"- **Mean Energy**: {energy_stats.get('mean', 0):.4f}\n")
            f.write(f"- **Energy Std**: {energy_stats.get('std', 0):.4f}\n")
        
        # Convergence stats
        convergence_stats = metrics.get('convergence_stats', {})
        if convergence_stats:
            f.write(f"- **Success Rate**: {convergence_stats.get('success_rate', 0):.2%}\n")
        
        f.write("\n")
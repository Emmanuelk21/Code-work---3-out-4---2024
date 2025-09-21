"""Main pipeline for QML vs CML IDR prediction comparison."""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import pickle
import json

from ..utils.config import get_config
from ..utils.logging import get_logger, ProgressLogger
from ..data.pdbbind_handler import PDBbindHandler
from ..data.idr_detector import IDRDetector
from ..data.preprocessor import DatasetProcessor
from ..classical.alphafold_baseline import AlphaFold3Baseline
from ..quantum.vqe_framework import VQEIDRSolver
from ..evaluation.metrics import ComparativeAnalysis

logger = get_logger(__name__)


class IDRPredictionPipeline:
    """Main pipeline for comparing QML and CML IDR predictions."""
    
    def __init__(self, config_path: str = None, output_dir: str = None):
        """Initialize pipeline.
        
        Args:
            config_path: Path to configuration file
            output_dir: Output directory for results
        """
        # Load configuration
        if config_path:
            from ..utils.config import load_config, set_config
            config = load_config(config_path)
            set_config(config)
        
        self.config = get_config()
        
        # Set up output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(self.config.output.results_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.pdbbind_handler = PDBbindHandler()
        self.idr_detector = IDRDetector()
        self.dataset_processor = DatasetProcessor()
        self.alphafold_baseline = None
        self.vqe_solver = None
        self.comparative_analysis = ComparativeAnalysis()
        
        # Results storage
        self.results = {
            'dataset_info': {},
            'qml_results': [],
            'cml_results': [],
            'comparison_results': {},
            'metadata': {
                'pipeline_version': '1.0.0',
                'start_time': None,
                'end_time': None,
                'total_runtime': None,
                'config': self.config.__dict__
            }
        }
    
    def run_full_pipeline(self, max_fragments: int = None) -> Dict:
        """Run the complete QML vs CML comparison pipeline.
        
        Args:
            max_fragments: Maximum number of fragments to process (for testing)
            
        Returns:
            Dictionary with complete results
        """
        logger.info("Starting full QML vs CML IDR prediction pipeline")
        start_time = time.time()
        self.results['metadata']['start_time'] = start_time
        
        try:
            # Step 1: Dataset preparation
            logger.info("Step 1: Dataset preparation")
            idr_dataset = self.prepare_dataset(max_fragments)
            
            if idr_dataset.empty:
                raise ValueError("No IDR fragments found in dataset")
            
            # Step 2: Classical ML baseline
            logger.info("Step 2: Running Classical ML baseline")
            cml_results = self.run_classical_baseline(idr_dataset)
            
            # Step 3: Quantum ML predictions
            logger.info("Step 3: Running Quantum ML predictions")
            qml_results = self.run_quantum_predictions(idr_dataset)
            
            # Step 4: Comparative analysis
            logger.info("Step 4: Performing comparative analysis")
            comparison_results = self.run_comparative_analysis(qml_results, cml_results)
            
            # Step 5: Generate reports
            logger.info("Step 5: Generating reports")
            self.generate_reports(comparison_results)
            
            # Finalize results
            end_time = time.time()
            self.results['metadata']['end_time'] = end_time
            self.results['metadata']['total_runtime'] = end_time - start_time
            
            # Save complete results
            self.save_results()
            
            logger.info(f"Pipeline completed successfully in {end_time - start_time:.2f} seconds")
            return self.results
        
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
    
    def prepare_dataset(self, max_fragments: int = None) -> pd.DataFrame:
        """Prepare IDR dataset from PDBbind.
        
        Args:
            max_fragments: Maximum number of fragments to process
            
        Returns:
            DataFrame with IDR fragments
        """
        logger.info("Preparing IDR dataset from PDBbind")
        
        # Download and process PDBbind data
        logger.info("Processing PDBbind dataset...")
        rubisco_df = self.pdbbind_handler.process_rubisco_dataset()
        
        # Extract IDR fragments
        logger.info("Extracting IDR fragments...")
        idr_df = self.idr_detector.process_rubisco_idrs(rubisco_df)
        
        # Limit fragments if requested
        if max_fragments and len(idr_df) > max_fragments:
            logger.info(f"Limiting dataset to {max_fragments} fragments")
            idr_df = idr_df.head(max_fragments).copy()
        
        # Process features
        logger.info("Processing features for ML training...")
        processed_features = self.dataset_processor.process_idr_dataset(idr_df)
        
        # Save processed dataset
        dataset_file = self.dataset_processor.save_processed_dataset(processed_features)
        
        # Store dataset info
        self.results['dataset_info'] = {
            'n_fragments': len(idr_df),
            'n_structures': rubisco_df['pdb_code'].nunique() if not rubisco_df.empty else 0,
            'fragment_lengths': idr_df['length'].tolist() if not idr_df.empty else [],
            'mean_disorder_score': idr_df['avg_disorder_score'].mean() if not idr_df.empty else 0,
            'dataset_file': str(dataset_file),
            'features_available': list(processed_features.keys())
        }
        
        logger.info(f"Dataset prepared with {len(idr_df)} IDR fragments")
        return idr_df
    
    def run_classical_baseline(self, idr_dataset: pd.DataFrame) -> List[Dict]:
        """Run AlphaFold3 classical baseline.
        
        Args:
            idr_dataset: IDR fragments dataset
            
        Returns:
            List of CML prediction results
        """
        logger.info("Running AlphaFold3 classical baseline")
        
        # Initialize AlphaFold3 baseline
        self.alphafold_baseline = AlphaFold3Baseline()
        
        cml_results = []
        progress = ProgressLogger(logger, len(idr_dataset))
        
        for idx, row in idr_dataset.iterrows():
            try:
                fragment_id = f"{row['pdb_code']}_{row['chain_id']}_{row['start_residue']}_{row['end_residue']}"
                sequence = row['sequence']
                
                progress.step(f"Processing fragment {fragment_id}")
                
                # Run ensemble prediction
                start_time = time.time()
                predicted_structures = self.alphafold_baseline.predict_idr_ensemble(
                    sequence, fragment_id, self.config.evaluation.ensemble_size
                )
                runtime = time.time() - start_time
                
                # Evaluate predictions
                evaluation_results = self.alphafold_baseline.evaluate_predictions(predicted_structures)
                
                # Store results
                result = {
                    'fragment_id': fragment_id,
                    'method': 'AlphaFold3',
                    'sequence': sequence,
                    'n_predicted_structures': len(predicted_structures),
                    'predicted_structure_files': [str(f) for f in predicted_structures],
                    'runtime': runtime,
                    'converged': len(predicted_structures) > 0,
                    'evaluation': evaluation_results,
                    'metadata': {
                        'pdb_code': row['pdb_code'],
                        'chain_id': row['chain_id'],
                        'start_residue': row['start_residue'],
                        'end_residue': row['end_residue'],
                        'length': row['length']
                    }
                }
                
                # Add energy estimation (simplified)
                if predicted_structures:
                    # Use first structure for energy calculation
                    coords = self._extract_coordinates_from_pdb(predicted_structures[0])
                    if coords is not None:
                        energy_metrics = self.comparative_analysis.energy_metrics.calculate_potential_energy(
                            coords, sequence
                        )
                        result['total_potential_energy'] = energy_metrics['total_potential_energy']
                
                cml_results.append(result)
                
            except Exception as e:
                logger.error(f"Classical prediction failed for fragment {idx}: {e}")
                # Add failed result
                cml_results.append({
                    'fragment_id': f"fragment_{idx}",
                    'method': 'AlphaFold3',
                    'sequence': row.get('sequence', ''),
                    'runtime': 0,
                    'converged': False,
                    'error': str(e)
                })
        
        self.results['cml_results'] = cml_results
        logger.info(f"Completed classical baseline with {len(cml_results)} predictions")
        
        return cml_results
    
    def run_quantum_predictions(self, idr_dataset: pd.DataFrame) -> List[Dict]:
        """Run VQE quantum predictions.
        
        Args:
            idr_dataset: IDR fragments dataset
            
        Returns:
            List of QML prediction results
        """
        logger.info("Running VQE quantum predictions")
        
        qml_results = []
        progress = ProgressLogger(logger, len(idr_dataset))
        
        for idx, row in idr_dataset.iterrows():
            try:
                fragment_id = f"{row['pdb_code']}_{row['chain_id']}_{row['start_residue']}_{row['end_residue']}"
                sequence = row['sequence']
                
                progress.step(f"Processing fragment {fragment_id}")
                
                # Limit sequence length for quantum simulation
                max_qubits = min(len(sequence), self.config.quantum.simulator.max_qubits)
                truncated_sequence = sequence[:max_qubits]
                
                # Initialize VQE solver
                if self.vqe_solver is None or self.vqe_solver.n_qubits != max_qubits:
                    self.vqe_solver = VQEIDRSolver(
                        n_qubits=max_qubits,
                        ansatz_type=self.config.quantum.vqe.get('ansatz_type', 'hardware_efficient')
                    )
                
                # Get initial coordinates
                coords = self._get_fragment_coordinates(row)
                if coords is None:
                    logger.warning(f"No coordinates available for fragment {fragment_id}")
                    continue
                
                # Truncate coordinates to match sequence
                coords = coords[:len(truncated_sequence)]
                
                # Run ensemble prediction with different stress conditions
                stress_conditions_list = [
                    {'perturbation_factor': 0.0, 'condition': 'normal'},
                    {'perturbation_factor': 0.05, 'condition': 'mild_stress'},
                    {'perturbation_factor': 0.1, 'condition': 'high_stress'},
                    {'perturbation_factor': -0.05, 'condition': 'favorable'},
                    {'perturbation_factor': 0.0, 'condition': 'normal_repeat'}
                ]
                
                start_time = time.time()
                ensemble_results = self.vqe_solver.run_ensemble_prediction(
                    truncated_sequence, coords, 
                    self.config.evaluation.ensemble_size,
                    stress_conditions_list
                )
                runtime = time.time() - start_time
                
                # Aggregate ensemble results
                successful_predictions = [r for r in ensemble_results if r.get('converged', False)]
                
                result = {
                    'fragment_id': fragment_id,
                    'method': 'VQE',
                    'sequence': sequence,
                    'truncated_sequence': truncated_sequence,
                    'n_qubits_used': max_qubits,
                    'ensemble_size': len(ensemble_results),
                    'successful_predictions': len(successful_predictions),
                    'runtime': runtime,
                    'converged': len(successful_predictions) > 0,
                    'ensemble_results': ensemble_results,
                    'metadata': {
                        'pdb_code': row['pdb_code'],
                        'chain_id': row['chain_id'],
                        'start_residue': row['start_residue'],
                        'end_residue': row['end_residue'],
                        'length': row['length'],
                        'original_length': len(sequence)
                    }
                }
                
                # Add aggregated metrics from successful predictions
                if successful_predictions:
                    energies = [r['ground_state_energy'] for r in successful_predictions]
                    optimization_steps = [r['optimization_steps'] for r in successful_predictions]
                    
                    result.update({
                        'ground_state_energy': np.mean(energies),
                        'energy_std': np.std(energies),
                        'mean_optimization_steps': np.mean(optimization_steps),
                        'predicted_coordinates': successful_predictions[0]['predicted_coordinates']  # Use first successful prediction
                    })
                
                qml_results.append(result)
                
            except Exception as e:
                logger.error(f"Quantum prediction failed for fragment {idx}: {e}")
                # Add failed result
                qml_results.append({
                    'fragment_id': f"fragment_{idx}",
                    'method': 'VQE',
                    'sequence': row.get('sequence', ''),
                    'runtime': 0,
                    'converged': False,
                    'error': str(e)
                })
        
        self.results['qml_results'] = qml_results
        logger.info(f"Completed quantum predictions with {len(qml_results)} results")
        
        return qml_results
    
    def run_comparative_analysis(self, qml_results: List[Dict], 
                               cml_results: List[Dict]) -> Dict:
        """Run comparative analysis between QML and CML results.
        
        Args:
            qml_results: QML prediction results
            cml_results: CML prediction results
            
        Returns:
            Comparative analysis results
        """
        logger.info("Running comparative analysis")
        
        # Perform comparison
        comparison_results = self.comparative_analysis.compare_methods(
            qml_results, cml_results
        )
        
        self.results['comparison_results'] = comparison_results
        
        return comparison_results
    
    def generate_reports(self, comparison_results: Dict):
        """Generate analysis reports.
        
        Args:
            comparison_results: Results from comparative analysis
        """
        logger.info("Generating analysis reports")
        
        # Generate main comparison report
        report_file = self.output_dir / "qml_vs_cml_comparison_report.md"
        self.comparative_analysis.generate_report(comparison_results, report_file)
        
        # Generate summary statistics
        self._generate_summary_statistics()
        
        # Generate visualizations (placeholder)
        self._generate_visualizations()
        
        logger.info(f"Reports generated in {self.output_dir}")
    
    def _generate_summary_statistics(self):
        """Generate summary statistics."""
        summary_file = self.output_dir / "summary_statistics.json"
        
        summary = {
            'dataset_summary': self.results['dataset_info'],
            'qml_summary': self._summarize_method_results(self.results['qml_results']),
            'cml_summary': self._summarize_method_results(self.results['cml_results']),
            'comparison_summary': self.results['comparison_results'].get('performance_summary', {})
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Summary statistics saved to {summary_file}")
    
    def _summarize_method_results(self, results: List[Dict]) -> Dict:
        """Summarize results for a method.
        
        Args:
            results: List of prediction results
            
        Returns:
            Summary dictionary
        """
        if not results:
            return {}
        
        successful = [r for r in results if r.get('converged', False)]
        runtimes = [r['runtime'] for r in results if 'runtime' in r]
        
        summary = {
            'total_predictions': len(results),
            'successful_predictions': len(successful),
            'success_rate': len(successful) / len(results) if results else 0,
            'mean_runtime': np.mean(runtimes) if runtimes else 0,
            'total_runtime': sum(runtimes) if runtimes else 0
        }
        
        # Add method-specific metrics
        if results[0].get('method') == 'VQE':
            energies = [r['ground_state_energy'] for r in successful if 'ground_state_energy' in r]
            if energies:
                summary.update({
                    'mean_energy': np.mean(energies),
                    'energy_std': np.std(energies)
                })
        
        elif results[0].get('method') == 'AlphaFold3':
            n_structures = [r['n_predicted_structures'] for r in results if 'n_predicted_structures' in r]
            if n_structures:
                summary['mean_structures_per_prediction'] = np.mean(n_structures)
        
        return summary
    
    def _generate_visualizations(self):
        """Generate visualization plots (placeholder)."""
        # This would generate plots comparing QML vs CML performance
        # For now, just create a placeholder
        viz_dir = self.output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        placeholder_file = viz_dir / "plots_placeholder.txt"
        with open(placeholder_file, 'w') as f:
            f.write("Visualization plots would be generated here:\n")
            f.write("- Runtime comparison\n")
            f.write("- Energy distribution\n")
            f.write("- RMSD comparison\n")
            f.write("- Success rate comparison\n")
            f.write("- Structural metrics comparison\n")
    
    def _get_fragment_coordinates(self, row: pd.Series) -> Optional[np.ndarray]:
        """Get coordinates for a fragment.
        
        Args:
            row: DataFrame row with fragment information
            
        Returns:
            Coordinates array or None
        """
        try:
            pdb_file = Path(row['pdb_file'])
            if not pdb_file.exists():
                return None
            
            coords = self.idr_detector.extract_coordinates_from_pdb(
                pdb_file, row['chain_id'],
                row['start_residue'], row['end_residue']
            )
            
            return coords
        
        except Exception as e:
            logger.error(f"Failed to extract coordinates: {e}")
            return None
    
    def _extract_coordinates_from_pdb(self, pdb_file: Path) -> Optional[np.ndarray]:
        """Extract coordinates from PDB file.
        
        Args:
            pdb_file: PDB file path
            
        Returns:
            Coordinates array or None
        """
        try:
            from Bio.PDB import PDBParser
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure('protein', pdb_file)
            
            coords = []
            for model in structure:
                for chain in model:
                    for residue in chain:
                        if residue.get_id()[0] == ' ':
                            # Extract backbone atoms
                            backbone_coords = []
                            for atom_name in ['N', 'CA', 'C', 'O']:
                                if atom_name in residue:
                                    backbone_coords.append(residue[atom_name].get_coord())
                                else:
                                    # Use last known position if atom missing
                                    if backbone_coords:
                                        backbone_coords.append(backbone_coords[-1])
                                    else:
                                        backbone_coords.append([0.0, 0.0, 0.0])
                            
                            coords.append(backbone_coords)
            
            return np.array(coords) if coords else None
        
        except Exception as e:
            logger.error(f"Failed to extract coordinates from {pdb_file}: {e}")
            return None
    
    def save_results(self):
        """Save complete pipeline results."""
        results_file = self.output_dir / "complete_results.pkl"
        
        with open(results_file, 'wb') as f:
            pickle.dump(self.results, f)
        
        # Also save as JSON (without complex objects)
        json_results = self._prepare_json_results()
        json_file = self.output_dir / "complete_results.json"
        
        with open(json_file, 'w') as f:
            json.dump(json_results, f, indent=2, default=str)
        
        logger.info(f"Complete results saved to {results_file} and {json_file}")
    
    def _prepare_json_results(self) -> Dict:
        """Prepare results for JSON serialization."""
        json_results = {}
        
        for key, value in self.results.items():
            if key == 'qml_results' or key == 'cml_results':
                # Simplify complex results for JSON
                simplified_results = []
                for result in value:
                    simplified = {k: v for k, v in result.items() 
                                if not isinstance(v, (np.ndarray, complex))}
                    
                    # Convert numpy arrays to lists
                    for k, v in result.items():
                        if isinstance(v, np.ndarray):
                            simplified[k] = v.tolist()
                    
                    simplified_results.append(simplified)
                
                json_results[key] = simplified_results
            else:
                json_results[key] = value
        
        return json_results
    
    def load_results(self, results_file: str) -> Dict:
        """Load pipeline results from file.
        
        Args:
            results_file: Path to results file
            
        Returns:
            Loaded results dictionary
        """
        results_path = Path(results_file)
        
        if results_path.suffix == '.pkl':
            with open(results_path, 'rb') as f:
                results = pickle.load(f)
        elif results_path.suffix == '.json':
            with open(results_path, 'r') as f:
                results = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {results_path.suffix}")
        
        self.results = results
        logger.info(f"Results loaded from {results_path}")
        
        return results
    
    def cleanup(self):
        """Clean up temporary files and resources."""
        if self.alphafold_baseline:
            self.alphafold_baseline.cleanup()
        
        logger.info("Pipeline cleanup completed")
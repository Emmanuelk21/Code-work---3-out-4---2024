#!/usr/bin/env python3
"""
Snakemake script for running Quantum ML predictions (VQE).
"""

import sys
import logging
import pickle
import json
import pandas as pd
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qml_idr.quantum.vqe_framework import VQEIDRSolver
from qml_idr.utils.logging import setup_logging
from qml_idr.data.preprocessor import DatasetProcessor

def main():
    # Set up logging
    logger = setup_logging()
    logger.info("Starting Quantum ML predictions with VQE")
    
    try:
        # Load processed dataset
        dataset_file = Path(snakemake.input.processed_dataset)
        dataset_info_file = Path(snakemake.input.dataset_info)
        
        # Load dataset info
        with open(dataset_info_file, 'r') as f:
            dataset_info = json.load(f)
        
        # Load processed features
        processor = DatasetProcessor()
        features = processor.load_processed_dataset(dataset_file.name)
        
        # Create DataFrame from features for processing
        idr_data = []
        for i, seq in enumerate(features['sequences']):
            metadata = features['metadata'][i]
            idr_data.append({
                'sequence': seq,
                'pdb_code': metadata['pdb_code'],
                'chain_id': metadata['chain_id'],
                'start_residue': metadata['start_residue'],
                'end_residue': metadata['end_residue'],
                'fragment_id': metadata['fragment_id'],
                'length': len(seq),
                'coordinates_index': i  # Index for coordinates lookup
            })
        
        idr_df = pd.DataFrame(idr_data)
        logger.info(f"Loaded {len(idr_df)} fragments for quantum ML prediction")
        
        # Prepare output directories
        output_results = Path(snakemake.output.qml_results)
        output_states = Path(snakemake.output.qml_states)
        
        output_results.parent.mkdir(parents=True, exist_ok=True)
        output_states.mkdir(parents=True, exist_ok=True)
        
        # Run predictions
        qml_results = []
        vqe_solver = None
        
        for idx, row in idr_df.iterrows():
            try:
                fragment_id = row['fragment_id']
                sequence = row['sequence']
                
                logger.info(f"Processing fragment {idx+1}/{len(idr_df)}: {fragment_id}")
                
                # Limit sequence length for quantum simulation
                max_qubits = min(len(sequence), 15)  # Conservative limit for simulation
                truncated_sequence = sequence[:max_qubits]
                
                # Initialize or reinitialize VQE solver if needed
                if vqe_solver is None or vqe_solver.n_qubits != max_qubits:
                    vqe_solver = VQEIDRSolver(
                        n_qubits=max_qubits,
                        ansatz_type='hardware_efficient'
                    )
                
                # Get coordinates from features
                coords_idx = row['coordinates_index']
                if coords_idx < len(features['coordinates']):
                    coords = np.array(features['coordinates'][coords_idx])
                    # Truncate coordinates to match sequence
                    coords = coords[:len(truncated_sequence)]
                else:
                    # Generate mock coordinates if not available
                    coords = np.random.random((len(truncated_sequence), 4, 3)) * 10
                    logger.warning(f"Using mock coordinates for {fragment_id}")
                
                # Run VQE prediction
                import time
                start_time = time.time()
                
                # Define stress conditions for ensemble
                stress_conditions_list = [
                    {'perturbation_factor': 0.0, 'condition': 'normal'},
                    {'perturbation_factor': 0.05, 'condition': 'mild_stress'},
                    {'perturbation_factor': 0.1, 'condition': 'high_stress'}
                ]
                
                ensemble_results = vqe_solver.run_ensemble_prediction(
                    truncated_sequence, coords, 
                    n_runs=3,  # Reduced for speed
                    stress_conditions_list=stress_conditions_list
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
                    energies = [r['ground_state_energy'] for r in successful_predictions 
                              if 'ground_state_energy' in r and np.isfinite(r['ground_state_energy'])]
                    optimization_steps = [r['optimization_steps'] for r in successful_predictions]
                    
                    if energies:
                        result.update({
                            'ground_state_energy': np.mean(energies),
                            'energy_std': np.std(energies),
                            'mean_optimization_steps': np.mean(optimization_steps),
                            'predicted_coordinates': successful_predictions[0]['predicted_coordinates']
                        })
                    
                    # Save quantum states
                    state_file = output_states / f"{fragment_id}_quantum_states.pkl"
                    with open(state_file, 'wb') as f:
                        pickle.dump({
                            'fragment_id': fragment_id,
                            'ensemble_results': ensemble_results,
                            'successful_predictions': successful_predictions
                        }, f)
                
                qml_results.append(result)
                logger.info(f"Completed quantum prediction for {fragment_id}")
                
            except Exception as e:
                logger.error(f"Quantum prediction failed for fragment {idx}: {e}")
                # Add failed result
                qml_results.append({
                    'fragment_id': row.get('fragment_id', f'fragment_{idx}'),
                    'method': 'VQE',
                    'sequence': row.get('sequence', ''),
                    'runtime': 0,
                    'converged': False,
                    'error': str(e)
                })
        
        # Save results
        with open(output_results, 'wb') as f:
            pickle.dump(qml_results, f)
        
        logger.info(f"Quantum ML predictions completed. Saved {len(qml_results)} results to {output_results}")
        
        # Create states directory marker
        marker_file = output_states / ".quantum_states_saved"
        marker_file.touch()
        
    except Exception as e:
        logger.error(f"Quantum ML pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()
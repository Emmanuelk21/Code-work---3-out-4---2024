#!/usr/bin/env python3
"""
Snakemake script for running Classical ML baseline (AlphaFold3).
"""

import sys
import logging
import pickle
import json
import pandas as pd
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qml_idr.classical.alphafold_baseline import AlphaFold3Baseline
from qml_idr.utils.logging import setup_logging
from qml_idr.data.preprocessor import DatasetProcessor

def main():
    # Set up logging
    logger = setup_logging()
    logger.info("Starting Classical ML predictions with AlphaFold3")
    
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
                'length': len(seq)
            })
        
        idr_df = pd.DataFrame(idr_data)
        logger.info(f"Loaded {len(idr_df)} fragments for classical ML prediction")
        
        # Initialize AlphaFold3 baseline
        af3_baseline = AlphaFold3Baseline()
        
        # Prepare output directories
        output_results = Path(snakemake.output.cml_results)
        output_structures = Path(snakemake.output.cml_structures)
        
        output_results.parent.mkdir(parents=True, exist_ok=True)
        output_structures.mkdir(parents=True, exist_ok=True)
        
        # Run predictions
        cml_results = []
        
        for idx, row in idr_df.iterrows():
            try:
                fragment_id = row['fragment_id']
                sequence = row['sequence']
                
                logger.info(f"Processing fragment {idx+1}/{len(idr_df)}: {fragment_id}")
                
                # Run AlphaFold3 prediction
                import time
                start_time = time.time()
                
                predicted_structures = af3_baseline.predict_idr_ensemble(
                    sequence, fragment_id, n_models=3  # Reduced for speed
                )
                
                runtime = time.time() - start_time
                
                # Evaluate predictions
                evaluation_results = af3_baseline.evaluate_predictions(predicted_structures)
                
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
                
                # Copy structures to output directory
                for i, struct_file in enumerate(predicted_structures):
                    output_struct = output_structures / f"{fragment_id}_model_{i}.pdb"
                    if struct_file.exists():
                        import shutil
                        shutil.copy2(struct_file, output_struct)
                        result['predicted_structure_files'][i] = str(output_struct)
                
                cml_results.append(result)
                logger.info(f"Completed prediction for {fragment_id}")
                
            except Exception as e:
                logger.error(f"Prediction failed for fragment {idx}: {e}")
                # Add failed result
                cml_results.append({
                    'fragment_id': row.get('fragment_id', f'fragment_{idx}'),
                    'method': 'AlphaFold3',
                    'sequence': row.get('sequence', ''),
                    'runtime': 0,
                    'converged': False,
                    'error': str(e)
                })
        
        # Save results
        with open(output_results, 'wb') as f:
            pickle.dump(cml_results, f)
        
        logger.info(f"Classical ML predictions completed. Saved {len(cml_results)} results to {output_results}")
        
        # Cleanup
        af3_baseline.cleanup()
        
    except Exception as e:
        logger.error(f"Classical ML pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()
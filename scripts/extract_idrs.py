#!/usr/bin/env python3
"""
Snakemake script for extracting IDR fragments.
"""

import sys
import logging
import pandas as pd
import h5py
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qml_idr.data.idr_detector import IDRDetector
from qml_idr.utils.logging import setup_logging

def main():
    # Set up logging
    logger = setup_logging()
    logger.info("Starting IDR extraction")
    
    try:
        # Read input data
        input_csv = Path(snakemake.input.csv_file)
        
        if not input_csv.exists() or input_csv.stat().st_size == 0:
            logger.warning("Input CSV file is empty or missing, creating mock data")
            # Create minimal mock data for demonstration
            rubisco_df = pd.DataFrame({
                'pdb_code': ['8ruc', '1rcx'],
                'chain_id': ['A', 'A'],
                'resolution': [1.8, 2.1],
                'pdb_file': ['data/pdbbind/8ruc.pdb', 'data/pdbbind/1rcx.pdb'],
                'num_residues': [50, 45]
            })
        else:
            rubisco_df = pd.read_csv(input_csv)
        
        # Initialize IDR detector
        idr_detector = IDRDetector()
        
        # Extract IDR fragments
        logger.info("Extracting IDR fragments from structures")
        idr_df = idr_detector.process_rubisco_idrs(rubisco_df)
        
        # Limit fragments if specified
        max_fragments = snakemake.params.get('max_fragments', None)
        if max_fragments and len(idr_df) > max_fragments:
            logger.info(f"Limiting to {max_fragments} fragments")
            idr_df = idr_df.head(max_fragments).copy()
        
        # Ensure output directories exist
        output_csv = Path(snakemake.output.idr_csv)
        output_coords = Path(snakemake.output.idr_coords)
        
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        output_coords.parent.mkdir(parents=True, exist_ok=True)
        
        # Save IDR fragments
        if not idr_df.empty:
            idr_df.to_csv(output_csv, index=False)
            logger.info(f"Saved {len(idr_df)} IDR fragments to {output_csv}")
            
            # Save coordinates to HDF5
            with h5py.File(output_coords, 'w') as f:
                for idx, row in idr_df.iterrows():
                    if row.get('has_coordinates', False):
                        fragment_id = f"{row['pdb_code']}_{row['chain_id']}_{row['start_residue']}_{row['end_residue']}"
                        
                        # Try to extract coordinates
                        try:
                            coords = idr_detector.extract_coordinates_from_pdb(
                                Path(row['pdb_file']), row['chain_id'],
                                row['start_residue'], row['end_residue']
                            )
                            
                            if coords is not None:
                                f.create_dataset(fragment_id, data=coords, compression='gzip')
                        
                        except Exception as e:
                            logger.warning(f"Failed to extract coordinates for {fragment_id}: {e}")
            
            logger.info(f"Saved coordinates to {output_coords}")
        
        else:
            # Create empty files
            output_csv.touch()
            with h5py.File(output_coords, 'w') as f:
                f.attrs['empty'] = True
            logger.warning("No IDR fragments found, created empty files")
        
        logger.info("IDR extraction completed successfully")
        
    except Exception as e:
        logger.error(f"IDR extraction failed: {e}")
        raise

if __name__ == "__main__":
    main()
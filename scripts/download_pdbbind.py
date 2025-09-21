#!/usr/bin/env python3
"""
Snakemake script for downloading and processing PDBbind dataset.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qml_idr.data.pdbbind_handler import PDBbindHandler
from qml_idr.utils.logging import setup_logging

def main():
    # Set up logging
    logger = setup_logging()
    logger.info("Starting PDBbind download and processing")
    
    try:
        # Initialize handler
        handler = PDBbindHandler()
        
        # Process RuBisCO dataset
        logger.info("Processing RuBisCO dataset from PDBbind")
        rubisco_df = handler.process_rubisco_dataset()
        
        # Ensure output files exist
        output_csv = Path(snakemake.output.csv_file)
        output_structures = Path(snakemake.output.structures)
        
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        output_structures.mkdir(parents=True, exist_ok=True)
        
        # Save results
        if not rubisco_df.empty:
            rubisco_df.to_csv(output_csv, index=False)
            logger.info(f"Saved {len(rubisco_df)} structures to {output_csv}")
        else:
            # Create empty file to satisfy Snakemake
            output_csv.touch()
            logger.warning("No RuBisCO structures found, created empty file")
        
        # Create structure directory marker
        marker_file = output_structures / ".structures_downloaded"
        marker_file.touch()
        
        logger.info("PDBbind processing completed successfully")
        
    except Exception as e:
        logger.error(f"PDBbind processing failed: {e}")
        raise

if __name__ == "__main__":
    main()
"""PDBbind dataset handler for downloading and processing protein-ligand complexes."""

import os
import requests
import tarfile
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from Bio import PDB
from Bio.PDB import PDBParser, PDBIO
import numpy as np

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PDBbindHandler:
    """Handler for PDBbind database operations."""
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize PDBbind handler.
        
        Args:
            data_dir: Directory to store PDBbind data
        """
        self.config = get_config()
        self.data_dir = Path(data_dir) if data_dir else Path(self.config.output.data_dir)
        self.pdbbind_dir = self.data_dir / "pdbbind"
        self.pdbbind_dir.mkdir(parents=True, exist_ok=True)
        
        self.parser = PDBParser(QUIET=True)
        self.io = PDBIO()
    
    def download_pdbbind_index(self) -> pd.DataFrame:
        """Download and parse PDBbind index file.
        
        Returns:
            DataFrame with PDBbind entries and metadata
        """
        index_file = self.pdbbind_dir / "INDEX_general_PL_data.2020"
        
        if not index_file.exists():
            logger.info("Downloading PDBbind index file...")
            # Note: This is a placeholder URL - actual PDBbind requires registration
            # Users need to manually download from http://www.pdbbind.org.cn/
            logger.warning(
                "PDBbind requires manual download. Please download the refined set "
                "from http://www.pdbbind.org.cn/ and extract to data/pdbbind/"
            )
            
            # Create a mock index for demonstration
            return self._create_mock_index()
        
        # Parse the actual index file
        return self._parse_index_file(index_file)
    
    def _create_mock_index(self) -> pd.DataFrame:
        """Create mock PDBbind index for demonstration."""
        mock_data = {
            'PDB_code': ['8ruc', '1rcx', '1aai', '3rbr', '1uzd', '2cba'],
            'resolution': [1.8, 2.1, 1.9, 2.3, 1.7, 2.0],
            'release_year': [2023, 2015, 2014, 2016, 2018, 2019],
            'Kd/Ki': ['4.50e-6', '1.20e-5', '8.30e-6', '2.10e-5', '6.70e-6', '3.40e-6'],
            'ligand': ['CO2', 'RBP', 'CO2', 'CO2', 'ATP', 'Mg2+'],
            'protein_family': ['RuBisCO', 'RuBisCO', 'RuBisCO', 'RuBisCO', 'kinase', 'carbonic_anhydrase']
        }
        
        df = pd.DataFrame(mock_data)
        df['resolution'] = pd.to_numeric(df['resolution'])
        return df
    
    def _parse_index_file(self, index_file: Path) -> pd.DataFrame:
        """Parse actual PDBbind index file.
        
        Args:
            index_file: Path to index file
            
        Returns:
            Parsed DataFrame
        """
        # PDBbind index format parsing
        columns = ['PDB_code', 'resolution', 'release_year', 'Kd/Ki', 'ligand', 'protein_family']
        
        data = []
        with open(index_file, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                
                parts = line.strip().split()
                if len(parts) >= 6:
                    data.append(parts[:6])
        
        df = pd.DataFrame(data, columns=columns)
        df['resolution'] = pd.to_numeric(df['resolution'], errors='coerce')
        df['release_year'] = pd.to_numeric(df['release_year'], errors='coerce')
        
        return df
    
    def filter_rubisco_entries(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter DataFrame for RuBisCO entries.
        
        Args:
            df: PDBbind DataFrame
            
        Returns:
            Filtered DataFrame with RuBisCO entries
        """
        rubisco_codes = [code.lower() for code in self.config.data.rubisco_pdbs]
        
        # Filter by PDB codes and resolution
        filtered = df[
            (df['PDB_code'].str.lower().isin(rubisco_codes)) &
            (df['resolution'] <= self.config.data.idr_settings.max_resolution)
        ].copy()
        
        logger.info(f"Found {len(filtered)} RuBisCO entries meeting criteria")
        return filtered
    
    def download_pdb_structure(self, pdb_code: str) -> Optional[Path]:
        """Download PDB structure file.
        
        Args:
            pdb_code: 4-letter PDB code
            
        Returns:
            Path to downloaded PDB file or None if failed
        """
        pdb_code = pdb_code.lower()
        pdb_file = self.pdbbind_dir / f"{pdb_code}.pdb"
        
        if pdb_file.exists():
            logger.debug(f"PDB file {pdb_code} already exists")
            return pdb_file
        
        # Download from RCSB PDB
        url = f"https://files.rcsb.org/download/{pdb_code}.pdb"
        
        try:
            logger.info(f"Downloading PDB structure {pdb_code}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(pdb_file, 'w') as f:
                f.write(response.text)
            
            logger.info(f"Successfully downloaded {pdb_code}")
            return pdb_file
            
        except requests.RequestException as e:
            logger.error(f"Failed to download {pdb_code}: {e}")
            return None
    
    def extract_protein_chains(self, pdb_file: Path) -> Dict[str, Path]:
        """Extract individual protein chains from PDB file.
        
        Args:
            pdb_file: Path to PDB file
            
        Returns:
            Dictionary mapping chain IDs to extracted chain files
        """
        pdb_code = pdb_file.stem
        structure = self.parser.get_structure(pdb_code, pdb_file)
        
        chain_files = {}
        
        for model in structure:
            for chain in model:
                chain_id = chain.get_id()
                
                # Skip non-protein chains (water, ligands, etc.)
                if not self._is_protein_chain(chain):
                    continue
                
                # Create new structure with single chain
                chain_structure = PDB.Structure.Structure(f"{pdb_code}_{chain_id}")
                chain_model = PDB.Model.Model(0)
                chain_structure.add(chain_model)
                chain_model.add(chain.copy())
                
                # Save chain to file
                chain_file = self.pdbbind_dir / f"{pdb_code}_{chain_id}.pdb"
                self.io.set_structure(chain_structure)
                self.io.save(str(chain_file))
                
                chain_files[chain_id] = chain_file
                logger.debug(f"Extracted chain {chain_id} from {pdb_code}")
        
        return chain_files
    
    def _is_protein_chain(self, chain) -> bool:
        """Check if chain contains protein residues.
        
        Args:
            chain: Bio.PDB Chain object
            
        Returns:
            True if chain is protein
        """
        protein_residues = {
            'ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLN', 'GLU', 'GLY',
            'HIS', 'ILE', 'LEU', 'LYS', 'MET', 'PHE', 'PRO', 'SER',
            'THR', 'TRP', 'TYR', 'VAL'
        }
        
        residue_count = 0
        protein_residue_count = 0
        
        for residue in chain:
            if residue.get_id()[0] == ' ':  # Standard residue
                residue_count += 1
                if residue.get_resname() in protein_residues:
                    protein_residue_count += 1
        
        # Consider it a protein chain if >80% are standard amino acids
        if residue_count == 0:
            return False
        
        return (protein_residue_count / residue_count) > 0.8
    
    def get_structure_info(self, pdb_file: Path) -> Dict:
        """Get basic information about PDB structure.
        
        Args:
            pdb_file: Path to PDB file
            
        Returns:
            Dictionary with structure information
        """
        pdb_code = pdb_file.stem
        structure = self.parser.get_structure(pdb_code, pdb_file)
        
        info = {
            'pdb_code': pdb_code,
            'num_models': len(structure),
            'chains': [],
            'num_residues': 0,
            'num_atoms': 0
        }
        
        for model in structure:
            for chain in model:
                if self._is_protein_chain(chain):
                    chain_info = {
                        'chain_id': chain.get_id(),
                        'num_residues': len([r for r in chain if r.get_id()[0] == ' ']),
                        'num_atoms': len([a for r in chain for a in r if r.get_id()[0] == ' '])
                    }
                    info['chains'].append(chain_info)
                    info['num_residues'] += chain_info['num_residues']
                    info['num_atoms'] += chain_info['num_atoms']
        
        return info
    
    def process_rubisco_dataset(self) -> pd.DataFrame:
        """Process complete RuBisCO dataset from PDBbind.
        
        Returns:
            DataFrame with processed RuBisCO structures
        """
        logger.info("Processing RuBisCO dataset from PDBbind...")
        
        # Download and filter index
        index_df = self.download_pdbbind_index()
        rubisco_df = self.filter_rubisco_entries(index_df)
        
        # Process each structure
        processed_data = []
        
        for _, row in rubisco_df.iterrows():
            pdb_code = row['PDB_code'].lower()
            
            # Download structure
            pdb_file = self.download_pdb_structure(pdb_code)
            if pdb_file is None:
                continue
            
            # Extract chains
            chain_files = self.extract_protein_chains(pdb_file)
            
            # Get structure info
            structure_info = self.get_structure_info(pdb_file)
            
            # Add to processed data
            for chain_info in structure_info['chains']:
                processed_data.append({
                    'pdb_code': pdb_code,
                    'chain_id': chain_info['chain_id'],
                    'resolution': row['resolution'],
                    'num_residues': chain_info['num_residues'],
                    'num_atoms': chain_info['num_atoms'],
                    'pdb_file': str(pdb_file),
                    'chain_file': str(chain_files.get(chain_info['chain_id'], '')),
                    'ligand': row.get('ligand', ''),
                    'binding_affinity': row.get('Kd/Ki', '')
                })
        
        processed_df = pd.DataFrame(processed_data)
        
        # Save processed dataset
        output_file = self.pdbbind_dir / "rubisco_processed.csv"
        processed_df.to_csv(output_file, index=False)
        logger.info(f"Saved processed RuBisCO dataset to {output_file}")
        
        return processed_df
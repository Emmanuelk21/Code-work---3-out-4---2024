"""
Data preprocessing pipeline for PDBbind dataset and RuBisCO IDR extraction.
"""

import os
import tarfile
import requests
import h5py
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from tqdm import tqdm
import logging

from Bio import PDB
from Bio.PDB import PDBParser, PDBIO, Select
from Bio.SeqUtils import seq1
import mdtraj as md
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

from config.settings import (
    PDBBIND_URL, PDBBIND_DIR, RUBISCO_PDB_IDS, DISORDER_THRESHOLD,
    MIN_IDR_LENGTH, MAX_IDR_LENGTH, DATA_DIR
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDBbindProcessor:
    """Main class for processing PDBbind dataset and extracting RuBisCO structures."""
    
    def __init__(self):
        self.pdbbind_dir = PDBBIND_DIR
        self.pdbbind_dir.mkdir(parents=True, exist_ok=True)
        self.parser = PDBParser(QUIET=True)
        
    def download_pdbbind(self) -> None:
        """Download and extract PDBbind dataset."""
        logger.info("Downloading PDBbind dataset...")
        
        # Check if already downloaded
        if (self.pdbbind_dir / "refined-set").exists():
            logger.info("PDBbind dataset already exists, skipping download.")
            return
            
        # Download the dataset
        response = requests.get(PDBBIND_URL, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(self.pdbbind_dir / "pdbbind.tar.gz", "wb") as f:
            with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        # Extract the dataset
        logger.info("Extracting PDBbind dataset...")
        with tarfile.open(self.pdbbind_dir / "pdbbind.tar.gz", "r:gz") as tar:
            tar.extractall(self.pdbbind_dir)
        
        # Clean up
        os.remove(self.pdbbind_dir / "pdbbind.tar.gz")
        logger.info("PDBbind dataset downloaded and extracted successfully.")
    
    def extract_rubisco_structures(self) -> Dict[str, str]:
        """Extract RuBisCO structures from PDBbind dataset."""
        logger.info("Extracting RuBisCO structures...")
        
        rubisco_structures = {}
        refined_dir = self.pdbbind_dir / "refined-set"
        
        if not refined_dir.exists():
            raise FileNotFoundError("Refined PDBbind dataset not found. Run download_pdbbind() first.")
        
        # Look for RuBisCO structures in the dataset
        for pdb_id in RUBISCO_PDB_IDS:
            pdb_file = refined_dir / f"{pdb_id.lower()}" / f"{pdb_id.lower()}_protein.pdb"
            if pdb_file.exists():
                rubisco_structures[pdb_id] = str(pdb_file)
                logger.info(f"Found RuBisCO structure: {pdb_id}")
            else:
                # Try to download from PDB if not in PDBbind
                logger.info(f"Downloading {pdb_id} from PDB...")
                pdb_file = self._download_from_pdb(pdb_id)
                if pdb_file:
                    rubisco_structures[pdb_id] = pdb_file
        
        return rubisco_structures
    
    def _download_from_pdb(self, pdb_id: str) -> Optional[str]:
        """Download structure from PDB."""
        try:
            pdb_file = self.pdbbind_dir / f"{pdb_id.lower()}.pdb"
            url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
            
            response = requests.get(url)
            if response.status_code == 200:
                with open(pdb_file, 'w') as f:
                    f.write(response.text)
                return str(pdb_file)
        except Exception as e:
            logger.warning(f"Failed to download {pdb_id}: {e}")
        return None
    
    def identify_idrs(self, structure_file: str) -> List[Dict]:
        """Identify intrinsically disordered regions using IUPred3-like approach."""
        logger.info(f"Identifying IDRs in {structure_file}")
        
        # Parse structure
        structure = self.parser.get_structure("protein", structure_file)
        
        idr_regions = []
        
        for model in structure:
            for chain in model:
                # Get sequence and coordinates
                sequence = self._get_sequence(chain)
                coordinates = self._get_coordinates(chain)
                
                if len(sequence) < MIN_IDR_LENGTH:
                    continue
                
                # Calculate disorder scores (simplified IUPred3-like)
                disorder_scores = self._calculate_disorder_scores(sequence, coordinates)
                
                # Find IDR regions
                idr_regions.extend(self._find_idr_regions(
                    sequence, disorder_scores, chain.id, structure_file
                ))
        
        return idr_regions
    
    def _get_sequence(self, chain) -> str:
        """Extract sequence from chain."""
        sequence = ""
        for residue in chain:
            if residue.id[0] == ' ' and residue.has_id('CA'):
                sequence += seq1(residue.resname)
        return sequence
    
    def _get_coordinates(self, chain) -> np.ndarray:
        """Extract CA coordinates from chain."""
        coordinates = []
        for residue in chain:
            if residue.id[0] == ' ' and residue.has_id('CA'):
                ca = residue['CA']
                coordinates.append(ca.coord)
        return np.array(coordinates)
    
    def _calculate_disorder_scores(self, sequence: str, coordinates: np.ndarray) -> np.ndarray:
        """Calculate disorder scores based on structural properties."""
        scores = np.zeros(len(sequence))
        
        if len(coordinates) < 3:
            return scores
        
        # Calculate B-factors if available (simplified)
        # In real implementation, would use IUPred3 or similar
        for i in range(len(sequence)):
            # Simple heuristic: high flexibility in loops
            if i > 0 and i < len(coordinates) - 1:
                # Calculate local flexibility
                vec1 = coordinates[i] - coordinates[i-1]
                vec2 = coordinates[i+1] - coordinates[i]
                
                if np.linalg.norm(vec1) > 0 and np.linalg.norm(vec2) > 0:
                    angle = np.arccos(np.dot(vec1, vec2) / 
                                    (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
                    # Higher angles indicate more disorder
                    scores[i] = min(1.0, angle / np.pi)
        
        # Apply smoothing
        window_size = 5
        smoothed_scores = np.convolve(scores, np.ones(window_size)/window_size, mode='same')
        
        return smoothed_scores
    
    def _find_idr_regions(self, sequence: str, disorder_scores: np.ndarray, 
                         chain_id: str, structure_file: str) -> List[Dict]:
        """Find IDR regions based on disorder scores."""
        idr_regions = []
        
        in_idr = False
        start_idx = 0
        
        for i, score in enumerate(disorder_scores):
            if score > DISORDER_THRESHOLD and not in_idr:
                # Start of IDR
                in_idr = True
                start_idx = i
            elif score <= DISORDER_THRESHOLD and in_idr:
                # End of IDR
                in_idr = False
                end_idx = i
                
                # Check if IDR is within acceptable length range
                if MIN_IDR_LENGTH <= (end_idx - start_idx) <= MAX_IDR_LENGTH:
                    idr_region = {
                        'pdb_id': Path(structure_file).stem,
                        'chain_id': chain_id,
                        'start_residue': start_idx + 1,  # 1-indexed
                        'end_residue': end_idx,
                        'sequence': sequence[start_idx:end_idx],
                        'length': end_idx - start_idx,
                        'disorder_scores': disorder_scores[start_idx:end_idx].tolist(),
                        'structure_file': structure_file
                    }
                    idr_regions.append(idr_region)
        
        # Handle case where IDR extends to end of sequence
        if in_idr and len(sequence) - start_idx >= MIN_IDR_LENGTH:
            end_idx = len(sequence)
            if end_idx - start_idx <= MAX_IDR_LENGTH:
                idr_region = {
                    'pdb_id': Path(structure_file).stem,
                    'chain_id': chain_id,
                    'start_residue': start_idx + 1,
                    'end_residue': end_idx,
                    'sequence': sequence[start_idx:end_idx],
                    'length': end_idx - start_idx,
                    'disorder_scores': disorder_scores[start_idx:end_idx].tolist(),
                    'structure_file': structure_file
                }
                idr_regions.append(idr_region)
        
        return idr_regions
    
    def extract_idr_fragments(self, idr_regions: List[Dict]) -> List[Dict]:
        """Extract IDR fragments for quantum simulation."""
        logger.info("Extracting IDR fragments...")
        
        fragments = []
        
        for region in idr_regions:
            # Parse structure to extract fragment coordinates
            structure = self.parser.get_structure("protein", region['structure_file'])
            
            for model in structure:
                for chain in model:
                    if chain.id == region['chain_id']:
                        # Extract fragment coordinates
                        fragment_coords = self._extract_fragment_coords(
                            chain, region['start_residue'], region['end_residue']
                        )
                        
                        if fragment_coords is not None:
                            fragment = {
                                **region,
                                'coordinates': fragment_coords,
                                'dihedral_angles': self._calculate_dihedral_angles(fragment_coords),
                                'qubit_count': self._estimate_qubit_count(region['length'])
                            }
                            fragments.append(fragment)
        
        return fragments
    
    def _extract_fragment_coords(self, chain, start_residue: int, end_residue: int) -> Optional[np.ndarray]:
        """Extract coordinates for a specific fragment."""
        coords = []
        residue_count = 0
        
        for residue in chain:
            if residue.id[0] == ' ' and residue.has_id('CA'):
                residue_count += 1
                if start_residue <= residue_count <= end_residue:
                    if residue.has_id('CA'):
                        coords.append(residue['CA'].coord)
                    else:
                        return None  # Missing CA atom
        
        return np.array(coords) if len(coords) == (end_residue - start_residue + 1) else None
    
    def _calculate_dihedral_angles(self, coordinates: np.ndarray) -> np.ndarray:
        """Calculate phi and psi dihedral angles from coordinates."""
        if len(coordinates) < 4:
            return np.array([])
        
        # Simplified dihedral calculation (would need N, CA, C atoms in real implementation)
        angles = []
        for i in range(1, len(coordinates) - 2):
            # Calculate angle between consecutive vectors
            vec1 = coordinates[i] - coordinates[i-1]
            vec2 = coordinates[i+1] - coordinates[i]
            vec3 = coordinates[i+2] - coordinates[i+1]
            
            # Calculate dihedral angle
            v1 = np.cross(vec1, vec2)
            v2 = np.cross(vec2, vec3)
            
            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                angle = np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
                angles.append(angle)
        
        return np.array(angles)
    
    def _estimate_qubit_count(self, length: int) -> int:
        """Estimate qubit count needed for quantum simulation."""
        # Rough estimate: 4-6 qubits per residue
        return min(length * 4, 30)  # Cap at 30 qubits for simulator limits
    
    def save_fragments(self, fragments: List[Dict], output_file: str) -> None:
        """Save IDR fragments to HDF5 file."""
        logger.info(f"Saving {len(fragments)} fragments to {output_file}")
        
        with h5py.File(output_file, 'w') as f:
            for i, fragment in enumerate(fragments):
                group = f.create_group(f'fragment_{i}')
                
                # Store metadata
                for key, value in fragment.items():
                    if key not in ['coordinates', 'dihedral_angles', 'disorder_scores']:
                        group.attrs[key] = value
                
                # Store arrays
                if 'coordinates' in fragment:
                    group.create_dataset('coordinates', data=fragment['coordinates'])
                if 'dihedral_angles' in fragment:
                    group.create_dataset('dihedral_angles', data=fragment['dihedral_angles'])
                if 'disorder_scores' in fragment:
                    group.create_dataset('disorder_scores', data=fragment['disorder_scores'])
    
    def load_fragments(self, input_file: str) -> List[Dict]:
        """Load IDR fragments from HDF5 file."""
        logger.info(f"Loading fragments from {input_file}")
        
        fragments = []
        
        with h5py.File(input_file, 'r') as f:
            for fragment_name in f.keys():
                group = f[fragment_name]
                
                fragment = {}
                
                # Load metadata
                for key, value in group.attrs.items():
                    fragment[key] = value
                
                # Load arrays
                if 'coordinates' in group:
                    fragment['coordinates'] = group['coordinates'][:]
                if 'dihedral_angles' in group:
                    fragment['dihedral_angles'] = group['dihedral_angles'][:]
                if 'disorder_scores' in group:
                    fragment['disorder_scores'] = group['disorder_scores'][:]
                
                fragments.append(fragment)
        
        return fragments


def main():
    """Main preprocessing pipeline."""
    processor = PDBbindProcessor()
    
    # Download and extract PDBbind
    processor.download_pdbbind()
    
    # Extract RuBisCO structures
    rubisco_structures = processor.extract_rubisco_structures()
    
    all_idr_regions = []
    
    # Process each RuBisCO structure
    for pdb_id, structure_file in rubisco_structures.items():
        logger.info(f"Processing {pdb_id}...")
        idr_regions = processor.identify_idrs(structure_file)
        all_idr_regions.extend(idr_regions)
    
    # Extract fragments
    fragments = processor.extract_idr_fragments(all_idr_regions)
    
    # Save results
    output_file = DATA_DIR / "rubisco_idr_fragments.h5"
    processor.save_fragments(fragments, str(output_file))
    
    logger.info(f"Preprocessing complete. Found {len(fragments)} IDR fragments.")
    logger.info(f"Results saved to {output_file}")


if __name__ == "__main__":
    main()
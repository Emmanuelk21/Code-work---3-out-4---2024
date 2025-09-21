"""Intrinsically Disordered Region (IDR) detection and analysis."""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from Bio import PDB
from Bio.PDB import PDBParser
from Bio.SeqUtils import seq1
import requests
import json

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class IDRDetector:
    """Detector for intrinsically disordered regions in protein structures."""
    
    def __init__(self):
        """Initialize IDR detector."""
        self.config = get_config()
        self.parser = PDBParser(QUIET=True)
        self.disorder_threshold = self.config.data.idr_settings.disorder_threshold
        self.min_length = self.config.data.idr_settings.min_fragment_length
        self.max_length = self.config.data.idr_settings.max_fragment_length
    
    def predict_disorder_iupred(self, sequence: str) -> np.ndarray:
        """Predict disorder using IUPred3 (simplified implementation).
        
        Args:
            sequence: Protein sequence
            
        Returns:
            Array of disorder scores (0-1) for each residue
        """
        # This is a simplified disorder predictor based on amino acid properties
        # In practice, you would use the actual IUPred3 tool or web service
        
        # Disorder-promoting amino acids (higher scores)
        disorder_propensity = {
            'A': 0.3, 'R': 0.7, 'N': 0.6, 'D': 0.8, 'C': 0.2,
            'Q': 0.6, 'E': 0.8, 'G': 0.4, 'H': 0.5, 'I': 0.1,
            'L': 0.1, 'K': 0.7, 'M': 0.2, 'F': 0.1, 'P': 0.9,
            'S': 0.5, 'T': 0.4, 'W': 0.1, 'Y': 0.2, 'V': 0.1
        }
        
        # Calculate raw scores
        raw_scores = np.array([disorder_propensity.get(aa, 0.5) for aa in sequence])
        
        # Apply smoothing window
        window_size = 7
        smoothed_scores = np.zeros_like(raw_scores)
        
        for i in range(len(sequence)):
            start = max(0, i - window_size // 2)
            end = min(len(sequence), i + window_size // 2 + 1)
            smoothed_scores[i] = np.mean(raw_scores[start:end])
        
        # Add some noise and context-dependent adjustments
        # Regions with many charged residues tend to be more disordered
        charge_density = self._calculate_charge_density(sequence, window_size=11)
        smoothed_scores += 0.2 * charge_density
        
        # Hydrophobic clusters reduce disorder
        hydrophobic_density = self._calculate_hydrophobic_density(sequence, window_size=7)
        smoothed_scores -= 0.3 * hydrophobic_density
        
        # Clip to valid range
        smoothed_scores = np.clip(smoothed_scores, 0, 1)
        
        return smoothed_scores
    
    def _calculate_charge_density(self, sequence: str, window_size: int = 11) -> np.ndarray:
        """Calculate local charge density."""
        charged_aa = {'R': 1, 'K': 1, 'D': -1, 'E': -1, 'H': 0.5}
        charges = np.array([charged_aa.get(aa, 0) for aa in sequence])
        
        density = np.zeros(len(sequence))
        for i in range(len(sequence)):
            start = max(0, i - window_size // 2)
            end = min(len(sequence), i + window_size // 2 + 1)
            density[i] = abs(np.sum(charges[start:end])) / (end - start)
        
        return density / max(density.max(), 1e-6)
    
    def _calculate_hydrophobic_density(self, sequence: str, window_size: int = 7) -> np.ndarray:
        """Calculate local hydrophobic density."""
        hydrophobic_aa = {'I', 'L', 'V', 'F', 'W', 'Y', 'M'}
        hydrophobic = np.array([1 if aa in hydrophobic_aa else 0 for aa in sequence])
        
        density = np.zeros(len(sequence))
        for i in range(len(sequence)):
            start = max(0, i - window_size // 2)
            end = min(len(sequence), i + window_size // 2 + 1)
            density[i] = np.sum(hydrophobic[start:end]) / (end - start)
        
        return density
    
    def extract_sequence_from_pdb(self, pdb_file: Path, chain_id: str = None) -> Dict[str, str]:
        """Extract protein sequence from PDB file.
        
        Args:
            pdb_file: Path to PDB file
            chain_id: Specific chain ID to extract (if None, extract all)
            
        Returns:
            Dictionary mapping chain IDs to sequences
        """
        structure = self.parser.get_structure('protein', pdb_file)
        sequences = {}
        
        for model in structure:
            for chain in model:
                if chain_id is not None and chain.get_id() != chain_id:
                    continue
                
                # Extract sequence
                residues = []
                for residue in chain:
                    if residue.get_id()[0] == ' ':  # Standard residue
                        try:
                            residues.append(seq1(residue.get_resname()))
                        except KeyError:
                            residues.append('X')  # Unknown amino acid
                
                if residues:
                    sequences[chain.get_id()] = ''.join(residues)
        
        return sequences
    
    def identify_idr_regions(self, sequence: str, disorder_scores: np.ndarray = None) -> List[Tuple[int, int, float]]:
        """Identify IDR regions in a protein sequence.
        
        Args:
            sequence: Protein sequence
            disorder_scores: Pre-calculated disorder scores (optional)
            
        Returns:
            List of tuples (start, end, avg_score) for each IDR region
        """
        if disorder_scores is None:
            disorder_scores = self.predict_disorder_iupred(sequence)
        
        # Find regions above disorder threshold
        disordered_mask = disorder_scores >= self.disorder_threshold
        
        # Find continuous regions
        regions = []
        start = None
        
        for i, is_disordered in enumerate(disordered_mask):
            if is_disordered and start is None:
                start = i
            elif not is_disordered and start is not None:
                end = i - 1
                length = end - start + 1
                
                if self.min_length <= length <= self.max_length:
                    avg_score = np.mean(disorder_scores[start:end+1])
                    regions.append((start, end, avg_score))
                
                start = None
        
        # Handle case where sequence ends with disordered region
        if start is not None:
            end = len(sequence) - 1
            length = end - start + 1
            
            if self.min_length <= length <= self.max_length:
                avg_score = np.mean(disorder_scores[start:end+1])
                regions.append((start, end, avg_score))
        
        logger.info(f"Found {len(regions)} IDR regions in sequence of length {len(sequence)}")
        
        return regions
    
    def extract_idr_fragments(self, pdb_file: Path, chain_id: str = None) -> List[Dict]:
        """Extract IDR fragments from PDB structure.
        
        Args:
            pdb_file: Path to PDB file
            chain_id: Specific chain ID (if None, process all chains)
            
        Returns:
            List of dictionaries with IDR fragment information
        """
        sequences = self.extract_sequence_from_pdb(pdb_file, chain_id)
        fragments = []
        
        for cid, sequence in sequences.items():
            if len(sequence) < self.min_length:
                continue
            
            # Predict disorder
            disorder_scores = self.predict_disorder_iupred(sequence)
            
            # Identify IDR regions
            idr_regions = self.identify_idr_regions(sequence, disorder_scores)
            
            # Extract fragment information
            for start, end, avg_score in idr_regions:
                fragment_sequence = sequence[start:end+1]
                
                fragment_info = {
                    'pdb_code': pdb_file.stem.split('_')[0],
                    'chain_id': cid,
                    'start_residue': start + 1,  # 1-based indexing
                    'end_residue': end + 1,
                    'length': len(fragment_sequence),
                    'sequence': fragment_sequence,
                    'avg_disorder_score': avg_score,
                    'disorder_scores': disorder_scores[start:end+1].tolist(),
                    'pdb_file': str(pdb_file)
                }
                
                fragments.append(fragment_info)
        
        return fragments
    
    def extract_coordinates_from_pdb(self, pdb_file: Path, chain_id: str, 
                                   start_residue: int, end_residue: int) -> Optional[np.ndarray]:
        """Extract coordinates for specific residue range.
        
        Args:
            pdb_file: Path to PDB file
            chain_id: Chain identifier
            start_residue: Start residue number (1-based)
            end_residue: End residue number (1-based)
            
        Returns:
            Array of coordinates [N_residues, N_atoms_per_residue, 3] or None
        """
        structure = self.parser.get_structure('protein', pdb_file)
        
        try:
            chain = structure[0][chain_id]
        except KeyError:
            logger.error(f"Chain {chain_id} not found in {pdb_file}")
            return None
        
        coordinates = []
        residue_numbers = []
        
        for residue in chain:
            if residue.get_id()[0] == ' ':  # Standard residue
                residue_numbers.append(residue.get_id()[1])
        
        # Find residues in range
        for residue in chain:
            if residue.get_id()[0] == ' ':
                res_num = residue.get_id()[1]
                
                # Convert to 0-based indexing for comparison
                if start_residue <= residue_numbers.index(res_num) + 1 <= end_residue:
                    # Extract backbone atoms (N, CA, C, O)
                    backbone_coords = []
                    for atom_name in ['N', 'CA', 'C', 'O']:
                        try:
                            atom = residue[atom_name]
                            backbone_coords.append(atom.get_coord())
                        except KeyError:
                            # If atom missing, use last known position
                            if backbone_coords:
                                backbone_coords.append(backbone_coords[-1])
                            else:
                                backbone_coords.append([0.0, 0.0, 0.0])
                    
                    coordinates.append(backbone_coords)
        
        if not coordinates:
            logger.warning(f"No coordinates found for residues {start_residue}-{end_residue}")
            return None
        
        return np.array(coordinates)
    
    def calculate_structural_features(self, coordinates: np.ndarray) -> Dict:
        """Calculate structural features from coordinates.
        
        Args:
            coordinates: Array of coordinates [N_residues, N_atoms, 3]
            
        Returns:
            Dictionary of structural features
        """
        if coordinates.size == 0:
            return {}
        
        # Calculate center of mass
        com = np.mean(coordinates.reshape(-1, 3), axis=0)
        
        # Calculate radius of gyration
        distances_to_com = np.linalg.norm(coordinates.reshape(-1, 3) - com, axis=1)
        rg = np.sqrt(np.mean(distances_to_com**2))
        
        # Calculate end-to-end distance (first CA to last CA)
        ca_coords = coordinates[:, 1, :]  # CA atoms
        end_to_end = np.linalg.norm(ca_coords[-1] - ca_coords[0])
        
        # Calculate average pairwise distance
        n_residues = len(ca_coords)
        pairwise_distances = []
        for i in range(n_residues):
            for j in range(i + 1, n_residues):
                dist = np.linalg.norm(ca_coords[i] - ca_coords[j])
                pairwise_distances.append(dist)
        
        avg_pairwise_distance = np.mean(pairwise_distances) if pairwise_distances else 0.0
        
        return {
            'radius_of_gyration': float(rg),
            'end_to_end_distance': float(end_to_end),
            'avg_pairwise_distance': float(avg_pairwise_distance),
            'center_of_mass': com.tolist(),
            'n_residues': n_residues
        }
    
    def process_rubisco_idrs(self, rubisco_df: pd.DataFrame) -> pd.DataFrame:
        """Process RuBisCO structures to extract IDR information.
        
        Args:
            rubisco_df: DataFrame with RuBisCO structure information
            
        Returns:
            DataFrame with IDR fragment information
        """
        logger.info("Processing RuBisCO structures for IDR extraction...")
        
        all_fragments = []
        
        for _, row in rubisco_df.iterrows():
            pdb_file = Path(row['pdb_file'])
            chain_id = row.get('chain_id', None)
            
            if not pdb_file.exists():
                logger.warning(f"PDB file not found: {pdb_file}")
                continue
            
            # Extract IDR fragments
            fragments = self.extract_idr_fragments(pdb_file, chain_id)
            
            for fragment in fragments:
                # Add original row information
                fragment.update({
                    'original_pdb_code': row['pdb_code'],
                    'resolution': row['resolution'],
                    'ligand': row.get('ligand', ''),
                    'binding_affinity': row.get('binding_affinity', '')
                })
                
                # Extract coordinates and calculate structural features
                coordinates = self.extract_coordinates_from_pdb(
                    pdb_file, fragment['chain_id'],
                    fragment['start_residue'], fragment['end_residue']
                )
                
                if coordinates is not None:
                    structural_features = self.calculate_structural_features(coordinates)
                    fragment.update(structural_features)
                    fragment['has_coordinates'] = True
                else:
                    fragment['has_coordinates'] = False
                
                all_fragments.append(fragment)
        
        idr_df = pd.DataFrame(all_fragments)
        
        # Filter fragments that meet criteria
        if not idr_df.empty:
            idr_df = idr_df[
                (idr_df['length'] >= self.min_length) &
                (idr_df['length'] <= self.max_length) &
                (idr_df['avg_disorder_score'] >= self.disorder_threshold) &
                (idr_df['has_coordinates'] == True)
            ].copy()
        
        logger.info(f"Extracted {len(idr_df)} IDR fragments meeting criteria")
        
        return idr_df
"""Data preprocessing and featurization for QML and CML pipelines."""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
from Bio import PDB
from Bio.PDB import PDBParser, Superimposer
from Bio.PDB.vectors import calc_dihedral
import h5py
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ProteinPreprocessor:
    """Preprocessor for protein structural data."""
    
    def __init__(self):
        """Initialize preprocessor."""
        self.config = get_config()
        self.parser = PDBParser(QUIET=True)
        self.superimposer = Superimposer()
        
        # Amino acid encoding
        self.aa_to_int = {
            'A': 0, 'R': 1, 'N': 2, 'D': 3, 'C': 4, 'Q': 5, 'E': 6, 'G': 7,
            'H': 8, 'I': 9, 'L': 10, 'K': 11, 'M': 12, 'F': 13, 'P': 14,
            'S': 15, 'T': 16, 'W': 17, 'Y': 18, 'V': 19, 'X': 20
        }
        
        # Physicochemical properties
        self.aa_properties = self._load_aa_properties()
        
    def _load_aa_properties(self) -> Dict[str, np.ndarray]:
        """Load amino acid physicochemical properties."""
        properties = {
            # [hydrophobicity, charge, volume, flexibility, aromaticity]
            'A': np.array([0.31, 0.0, 67.0, 0.36, 0.0]),
            'R': np.array([-1.01, 1.0, 148.0, 0.53, 0.0]),
            'N': np.array([-0.60, 0.0, 96.0, 0.46, 0.0]),
            'D': np.array([-0.77, -1.0, 91.0, 0.51, 0.0]),
            'C': np.array([1.54, 0.0, 86.0, 0.35, 0.0]),
            'Q': np.array([-0.22, 0.0, 114.0, 0.49, 0.0]),
            'E': np.array([-0.64, -1.0, 109.0, 0.50, 0.0]),
            'G': np.array([0.0, 0.0, 48.0, 0.54, 0.0]),
            'H': np.array([-0.40, 0.5, 118.0, 0.32, 1.0]),
            'I': np.array([1.80, 0.0, 124.0, 0.30, 0.0]),
            'L': np.array([1.70, 0.0, 124.0, 0.37, 0.0]),
            'K': np.array([-0.99, 1.0, 135.0, 0.47, 0.0]),
            'M': np.array([1.23, 0.0, 124.0, 0.34, 0.0]),
            'F': np.array([1.79, 0.0, 135.0, 0.31, 1.0]),
            'P': np.array([0.72, 0.0, 90.0, 0.13, 0.0]),
            'S': np.array([-0.04, 0.0, 73.0, 0.51, 0.0]),
            'T': np.array([0.26, 0.0, 93.0, 0.44, 0.0]),
            'W': np.array([2.25, 0.0, 163.0, 0.27, 1.0]),
            'Y': np.array([1.61, 0.0, 141.0, 0.30, 1.0]),
            'V': np.array([1.22, 0.0, 105.0, 0.33, 0.0]),
            'X': np.array([0.0, 0.0, 100.0, 0.40, 0.0])  # Unknown
        }
        return properties
    
    def extract_dihedral_angles(self, coordinates: np.ndarray) -> np.ndarray:
        """Extract phi and psi dihedral angles from backbone coordinates.
        
        Args:
            coordinates: Array of shape [N_residues, 4, 3] (N, CA, C, O atoms)
            
        Returns:
            Array of shape [N_residues-1, 2] with phi and psi angles
        """
        if coordinates.shape[1] < 4:
            raise ValueError("Need at least 4 atoms per residue (N, CA, C, O)")
        
        n_residues = coordinates.shape[0]
        angles = []
        
        for i in range(1, n_residues - 1):  # Skip first and last residue
            try:
                # Phi angle: C(i-1) - N(i) - CA(i) - C(i)
                phi = calc_dihedral(
                    coordinates[i-1, 2],  # C(i-1)
                    coordinates[i, 0],    # N(i)
                    coordinates[i, 1],    # CA(i)
                    coordinates[i, 2]     # C(i)
                )
                
                # Psi angle: N(i) - CA(i) - C(i) - N(i+1)
                psi = calc_dihedral(
                    coordinates[i, 0],    # N(i)
                    coordinates[i, 1],    # CA(i)
                    coordinates[i, 2],    # C(i)
                    coordinates[i+1, 0]   # N(i+1)
                )
                
                angles.append([phi, psi])
                
            except Exception as e:
                logger.warning(f"Failed to calculate angles for residue {i}: {e}")
                angles.append([0.0, 0.0])  # Default values
        
        return np.array(angles)
    
    def normalize_coordinates(self, coordinates: np.ndarray, 
                            reference: Optional[np.ndarray] = None) -> np.ndarray:
        """Normalize coordinates to a common reference frame.
        
        Args:
            coordinates: Array of coordinates to normalize
            reference: Reference coordinates for alignment (if None, use first structure)
            
        Returns:
            Normalized coordinates
        """
        if reference is None:
            # Use centered coordinates as reference
            centered = coordinates - np.mean(coordinates.reshape(-1, 3), axis=0)
            return centered
        
        # Align to reference using CA atoms (index 1)
        ca_coords = coordinates[:, 1, :]  # CA atoms
        ca_ref = reference[:, 1, :]
        
        # Perform superimposition
        self.superimposer.set_atoms(
            [PDB.Atom.Atom('CA', ca_ref[i], 0, 0, ' ', 'CA', i) for i in range(len(ca_ref))],
            [PDB.Atom.Atom('CA', ca_coords[i], 0, 0, ' ', 'CA', i) for i in range(len(ca_coords))]
        )
        
        # Apply transformation
        rotation, translation = self.superimposer.rotran
        
        aligned_coords = np.zeros_like(coordinates)
        for i in range(coordinates.shape[0]):
            for j in range(coordinates.shape[1]):
                aligned_coords[i, j] = np.dot(coordinates[i, j], rotation) + translation
        
        return aligned_coords
    
    def encode_sequence(self, sequence: str, method: str = 'onehot') -> np.ndarray:
        """Encode protein sequence using various methods.
        
        Args:
            sequence: Protein sequence
            method: Encoding method ('onehot', 'integer', 'properties')
            
        Returns:
            Encoded sequence
        """
        if method == 'onehot':
            encoding = np.zeros((len(sequence), 21))  # 20 AAs + unknown
            for i, aa in enumerate(sequence):
                aa_idx = self.aa_to_int.get(aa, 20)  # 20 for unknown
                encoding[i, aa_idx] = 1.0
            return encoding
        
        elif method == 'integer':
            return np.array([self.aa_to_int.get(aa, 20) for aa in sequence])
        
        elif method == 'properties':
            encoding = np.zeros((len(sequence), 5))  # 5 properties
            for i, aa in enumerate(sequence):
                encoding[i] = self.aa_properties.get(aa, self.aa_properties['X'])
            return encoding
        
        else:
            raise ValueError(f"Unknown encoding method: {method}")
    
    def create_distance_matrix(self, coordinates: np.ndarray) -> np.ndarray:
        """Create pairwise distance matrix from CA coordinates.
        
        Args:
            coordinates: Array of coordinates [N_residues, N_atoms, 3]
            
        Returns:
            Distance matrix [N_residues, N_residues]
        """
        ca_coords = coordinates[:, 1, :]  # CA atoms
        n_residues = len(ca_coords)
        
        distance_matrix = np.zeros((n_residues, n_residues))
        
        for i in range(n_residues):
            for j in range(n_residues):
                distance_matrix[i, j] = np.linalg.norm(ca_coords[i] - ca_coords[j])
        
        return distance_matrix
    
    def create_contact_map(self, coordinates: np.ndarray, cutoff: float = 8.0) -> np.ndarray:
        """Create binary contact map.
        
        Args:
            coordinates: Array of coordinates [N_residues, N_atoms, 3]
            cutoff: Distance cutoff for contacts (Angstroms)
            
        Returns:
            Binary contact map [N_residues, N_residues]
        """
        distance_matrix = self.create_distance_matrix(coordinates)
        contact_map = (distance_matrix <= cutoff).astype(float)
        
        # Remove self-contacts and adjacent residues
        for i in range(len(contact_map)):
            for j in range(max(0, i-1), min(len(contact_map), i+2)):
                contact_map[i, j] = 0.0
        
        return contact_map
    
    def calculate_energy_features(self, coordinates: np.ndarray, 
                                sequence: str) -> Dict[str, float]:
        """Calculate simplified energy-based features.
        
        Args:
            coordinates: Array of coordinates
            sequence: Protein sequence
            
        Returns:
            Dictionary of energy features
        """
        # Simplified energy calculations
        features = {}
        
        # Van der Waals energy (simplified)
        distance_matrix = self.create_distance_matrix(coordinates)
        vdw_energy = 0.0
        
        for i in range(len(distance_matrix)):
            for j in range(i + 2, len(distance_matrix)):  # Skip adjacent residues
                dist = distance_matrix[i, j]
                if dist > 0:
                    # Lennard-Jones like potential
                    vdw_energy += 4 * ((3.5 / dist)**12 - (3.5 / dist)**6)
        
        features['vdw_energy'] = vdw_energy
        
        # Electrostatic energy (simplified)
        charged_residues = {'R': 1, 'K': 1, 'D': -1, 'E': -1, 'H': 0.5}
        electrostatic_energy = 0.0
        
        for i, aa1 in enumerate(sequence):
            if aa1 in charged_residues:
                for j, aa2 in enumerate(sequence[i+2:], i+2):
                    if aa2 in charged_residues:
                        dist = distance_matrix[i, j]
                        if dist > 0:
                            charge_product = charged_residues[aa1] * charged_residues[aa2]
                            electrostatic_energy += charge_product / dist
        
        features['electrostatic_energy'] = electrostatic_energy
        
        # Solvation energy (simplified)
        # Based on solvent accessible surface area approximation
        hydrophobic_residues = {'A', 'I', 'L', 'M', 'F', 'W', 'Y', 'V'}
        solvation_energy = 0.0
        
        for i, aa in enumerate(sequence):
            # Count nearby residues (simplified burial)
            nearby_count = np.sum(distance_matrix[i] < 6.0) - 1  # Exclude self
            burial_factor = max(0, 1 - nearby_count / 10.0)  # Normalized burial
            
            if aa in hydrophobic_residues:
                solvation_energy += burial_factor * 2.0  # Favorable when buried
            else:
                solvation_energy -= burial_factor * 1.0  # Unfavorable when buried
        
        features['solvation_energy'] = solvation_energy
        features['total_energy'] = sum(features.values())
        
        return features


class QuantumFeatureEncoder:
    """Encoder for quantum machine learning features."""
    
    def __init__(self):
        """Initialize quantum feature encoder."""
        self.config = get_config()
        
    def encode_angles_to_quantum(self, angles: np.ndarray) -> List[float]:
        """Encode dihedral angles for quantum circuits.
        
        Args:
            angles: Array of phi/psi angles [N_residues, 2]
            
        Returns:
            List of parameters for quantum gates
        """
        # Normalize angles to [0, 2π] range
        normalized_angles = (angles + np.pi) % (2 * np.pi)
        
        # Flatten and return as parameter list
        return normalized_angles.flatten().tolist()
    
    def create_hamiltonian_matrix(self, coordinates: np.ndarray, 
                                sequence: str, 
                                interaction_cutoff: float = None) -> np.ndarray:
        """Create Hamiltonian matrix for VQE.
        
        Args:
            coordinates: Protein coordinates
            sequence: Protein sequence
            interaction_cutoff: Distance cutoff for interactions
            
        Returns:
            Hamiltonian matrix
        """
        if interaction_cutoff is None:
            interaction_cutoff = self.config.quantum.hamiltonian.interaction_cutoff
        
        n_residues = len(sequence)
        hamiltonian = np.zeros((n_residues, n_residues))
        
        # Calculate distance matrix
        preprocessor = ProteinPreprocessor()
        distance_matrix = preprocessor.create_distance_matrix(coordinates)
        
        # Single-site terms (diagonal)
        for i, aa in enumerate(sequence):
            # Local energy based on amino acid properties
            props = preprocessor.aa_properties.get(aa, preprocessor.aa_properties['X'])
            hamiltonian[i, i] = props[0]  # Hydrophobicity as local field
        
        # Interaction terms (off-diagonal)
        for i in range(n_residues):
            for j in range(i + 1, n_residues):
                dist = distance_matrix[i, j]
                
                if dist <= interaction_cutoff:
                    # Interaction strength based on distance and residue types
                    aa_i = sequence[i]
                    aa_j = sequence[j]
                    
                    props_i = preprocessor.aa_properties.get(aa_i, preprocessor.aa_properties['X'])
                    props_j = preprocessor.aa_properties.get(aa_j, preprocessor.aa_properties['X'])
                    
                    # Simple interaction model
                    interaction = -0.1 * np.exp(-dist / 3.0)  # Distance-dependent
                    interaction *= (props_i[0] * props_j[0])  # Hydrophobic interaction
                    
                    hamiltonian[i, j] = interaction
                    hamiltonian[j, i] = interaction  # Symmetric
        
        return hamiltonian
    
    def encode_stress_perturbations(self, base_hamiltonian: np.ndarray, 
                                  stress_type: str = 'temperature') -> np.ndarray:
        """Apply stress perturbations to Hamiltonian for climate simulation.
        
        Args:
            base_hamiltonian: Original Hamiltonian matrix
            stress_type: Type of stress ('temperature', 'co2', 'ph')
            
        Returns:
            Perturbed Hamiltonian
        """
        perturbation_factor = self.config.quantum.hamiltonian.stress_perturbation
        perturbed = base_hamiltonian.copy()
        
        if stress_type == 'temperature':
            # Increase interaction strengths (thermal stress)
            perturbed *= (1 + perturbation_factor)
        
        elif stress_type == 'co2':
            # Modify diagonal terms (CO2 binding effects)
            diagonal_indices = np.diag_indices_from(perturbed)
            perturbed[diagonal_indices] *= (1 + perturbation_factor)
        
        elif stress_type == 'ph':
            # Modify charged residue interactions
            # This is simplified - in practice would need sequence information
            perturbed += perturbation_factor * np.random.normal(0, 0.1, perturbed.shape)
        
        return perturbed


class DatasetProcessor:
    """Main processor for creating ML-ready datasets."""
    
    def __init__(self, output_dir: str = None):
        """Initialize dataset processor.
        
        Args:
            output_dir: Directory for processed datasets
        """
        self.config = get_config()
        self.output_dir = Path(output_dir) if output_dir else Path(self.config.output.data_dir) / "processed"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.protein_preprocessor = ProteinPreprocessor()
        self.quantum_encoder = QuantumFeatureEncoder()
        
    def process_idr_dataset(self, idr_df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Process IDR dataset for ML training.
        
        Args:
            idr_df: DataFrame with IDR fragment information
            
        Returns:
            Dictionary with processed features and targets
        """
        logger.info("Processing IDR dataset for ML training...")
        
        features = {
            'sequences': [],
            'coordinates': [],
            'dihedral_angles': [],
            'distance_matrices': [],
            'contact_maps': [],
            'sequence_encodings': [],
            'energy_features': [],
            'quantum_parameters': [],
            'hamiltonians': [],
            'structural_features': [],
            'metadata': []
        }
        
        valid_indices = []
        
        for idx, row in idr_df.iterrows():
            try:
                # Extract coordinates if available
                if row.get('has_coordinates', False):
                    pdb_file = Path(row['pdb_file'])
                    
                    # Load coordinates using IDR detector
                    from .idr_detector import IDRDetector
                    idr_detector = IDRDetector()
                    
                    coords = idr_detector.extract_coordinates_from_pdb(
                        pdb_file, row['chain_id'],
                        row['start_residue'], row['end_residue']
                    )
                    
                    if coords is None:
                        continue
                    
                    # Process coordinates
                    normalized_coords = self.protein_preprocessor.normalize_coordinates(coords)
                    
                    # Extract features
                    sequence = row['sequence']
                    dihedral_angles = self.protein_preprocessor.extract_dihedral_angles(coords)
                    distance_matrix = self.protein_preprocessor.create_distance_matrix(coords)
                    contact_map = self.protein_preprocessor.create_contact_map(coords)
                    sequence_encoding = self.protein_preprocessor.encode_sequence(sequence, 'properties')
                    energy_features = self.protein_preprocessor.calculate_energy_features(coords, sequence)
                    
                    # Quantum features
                    quantum_params = self.quantum_encoder.encode_angles_to_quantum(dihedral_angles)
                    hamiltonian = self.quantum_encoder.create_hamiltonian_matrix(coords, sequence)
                    
                    # Structural features
                    structural_features = {
                        'radius_of_gyration': row.get('radius_of_gyration', 0.0),
                        'end_to_end_distance': row.get('end_to_end_distance', 0.0),
                        'avg_pairwise_distance': row.get('avg_pairwise_distance', 0.0),
                        'length': row['length'],
                        'avg_disorder_score': row['avg_disorder_score']
                    }
                    
                    # Store features
                    features['sequences'].append(sequence)
                    features['coordinates'].append(normalized_coords)
                    features['dihedral_angles'].append(dihedral_angles)
                    features['distance_matrices'].append(distance_matrix)
                    features['contact_maps'].append(contact_map)
                    features['sequence_encodings'].append(sequence_encoding)
                    features['energy_features'].append(list(energy_features.values()))
                    features['quantum_parameters'].append(quantum_params)
                    features['hamiltonians'].append(hamiltonian)
                    features['structural_features'].append(list(structural_features.values()))
                    features['metadata'].append({
                        'pdb_code': row['pdb_code'],
                        'chain_id': row['chain_id'],
                        'start_residue': row['start_residue'],
                        'end_residue': row['end_residue'],
                        'fragment_id': f"{row['pdb_code']}_{row['chain_id']}_{row['start_residue']}_{row['end_residue']}"
                    })
                    
                    valid_indices.append(idx)
                    
            except Exception as e:
                logger.warning(f"Failed to process fragment {idx}: {e}")
                continue
        
        logger.info(f"Successfully processed {len(valid_indices)} fragments")
        
        # Convert to numpy arrays where appropriate
        processed_features = {}
        for key, value_list in features.items():
            if key in ['sequences', 'metadata']:
                processed_features[key] = value_list
            elif key in ['coordinates', 'distance_matrices', 'contact_maps', 'hamiltonians']:
                # Variable size arrays - keep as list
                processed_features[key] = value_list
            else:
                try:
                    processed_features[key] = np.array(value_list)
                except ValueError:
                    # Handle variable length arrays
                    processed_features[key] = value_list
        
        return processed_features
    
    def save_processed_dataset(self, features: Dict[str, np.ndarray], 
                             filename: str = "processed_idr_dataset.h5") -> Path:
        """Save processed dataset to HDF5 file.
        
        Args:
            features: Dictionary of processed features
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        output_file = self.output_dir / filename
        
        logger.info(f"Saving processed dataset to {output_file}")
        
        with h5py.File(output_file, 'w') as f:
            # Save arrays
            for key, data in features.items():
                if key in ['sequences', 'metadata']:
                    # Handle string data
                    if key == 'sequences':
                        dt = h5py.special_dtype(vlen=str)
                        f.create_dataset(key, data=data, dtype=dt)
                    else:
                        # Save metadata as JSON strings
                        import json
                        json_strings = [json.dumps(item) for item in data]
                        dt = h5py.special_dtype(vlen=str)
                        f.create_dataset(key, data=json_strings, dtype=dt)
                
                elif isinstance(data, np.ndarray):
                    f.create_dataset(key, data=data, compression='gzip')
                
                else:
                    # Handle variable-length arrays
                    group = f.create_group(key)
                    for i, item in enumerate(data):
                        group.create_dataset(str(i), data=np.array(item), compression='gzip')
        
        logger.info(f"Dataset saved successfully with {len(features['sequences'])} samples")
        return output_file
    
    def load_processed_dataset(self, filename: str = "processed_idr_dataset.h5") -> Dict:
        """Load processed dataset from HDF5 file.
        
        Args:
            filename: Input filename
            
        Returns:
            Dictionary of loaded features
        """
        input_file = self.output_dir / filename
        
        if not input_file.exists():
            raise FileNotFoundError(f"Processed dataset not found: {input_file}")
        
        logger.info(f"Loading processed dataset from {input_file}")
        
        features = {}
        
        with h5py.File(input_file, 'r') as f:
            for key in f.keys():
                if key in ['sequences']:
                    features[key] = [s.decode() if isinstance(s, bytes) else s for s in f[key][:]]
                
                elif key == 'metadata':
                    import json
                    json_strings = [s.decode() if isinstance(s, bytes) else s for s in f[key][:]]
                    features[key] = [json.loads(s) for s in json_strings]
                
                elif isinstance(f[key], h5py.Group):
                    # Variable-length arrays stored as groups
                    features[key] = []
                    for i in range(len(f[key].keys())):
                        features[key].append(f[key][str(i)][:])
                
                else:
                    features[key] = f[key][:]
        
        logger.info(f"Loaded dataset with {len(features['sequences'])} samples")
        return features
"""AlphaFold3-based classical ML baseline for IDR prediction."""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from Bio import PDB, SeqIO
from Bio.PDB import PDBParser, PDBIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
import requests
import json

from ..utils.config import get_config
from ..utils.logging import get_logger
from ..evaluation.metrics import StructuralMetrics

logger = get_logger(__name__)


class AlphaFold3Baseline:
    """AlphaFold3-based baseline for protein structure prediction."""
    
    def __init__(self, model_dir: str = None):
        """Initialize AlphaFold3 baseline.
        
        Args:
            model_dir: Directory containing AF3 model parameters
        """
        self.config = get_config()
        self.model_dir = Path(model_dir) if model_dir else Path("models/alphafold3")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="af3_"))
        
        self.parser = PDBParser(QUIET=True)
        self.io = PDBIO()
        self.metrics = StructuralMetrics()
        
        # AF3 configuration
        self.af3_config = {
            'num_ensemble': self.config.classical.alphafold3.num_ensemble,
            'num_recycles': self.config.classical.alphafold3.num_recycles,
            'early_stop_tolerance': self.config.classical.alphafold3.early_stop_tolerance,
            'confidence_threshold': self.config.classical.alphafold3.confidence_threshold
        }
        
        # Check if AF3 is available
        self._check_alphafold3_availability()
    
    def _check_alphafold3_availability(self) -> bool:
        """Check if AlphaFold3 is available and properly configured.
        
        Returns:
            True if AF3 is available
        """
        # Check for AF3 installation
        try:
            # This is a placeholder - actual AF3 installation check
            # In practice, you would check for the AF3 binary and model weights
            af3_binary = shutil.which('alphafold3') or shutil.which('run_alphafold.py')
            
            if af3_binary is None:
                logger.warning(
                    "AlphaFold3 not found in PATH. "
                    "Using mock predictions for demonstration. "
                    "Please install AF3 from https://github.com/deepmind/alphafold3"
                )
                self.use_mock = True
                return False
            
            # Check for model parameters
            if not self.model_dir.exists():
                logger.warning(f"AF3 model directory not found: {self.model_dir}")
                self.use_mock = True
                return False
            
            self.use_mock = False
            return True
            
        except Exception as e:
            logger.error(f"Error checking AF3 availability: {e}")
            self.use_mock = True
            return False
    
    def prepare_input_files(self, sequence: str, fragment_id: str, 
                          include_ligands: bool = False) -> Dict[str, Path]:
        """Prepare input files for AlphaFold3 prediction.
        
        Args:
            sequence: Protein sequence
            fragment_id: Unique identifier for the fragment
            include_ligands: Whether to include ligands (CO2, Mg2+)
            
        Returns:
            Dictionary with paths to input files
        """
        input_dir = self.temp_dir / fragment_id
        input_dir.mkdir(parents=True, exist_ok=True)
        
        # Create FASTA file
        fasta_file = input_dir / f"{fragment_id}.fasta"
        seq_record = SeqRecord(Seq(sequence), id=fragment_id, description="IDR fragment")
        
        with open(fasta_file, 'w') as f:
            SeqIO.write(seq_record, f, "fasta")
        
        # Create features file (simplified MSA)
        features_file = input_dir / f"{fragment_id}_features.pkl"
        
        # In practice, you would generate MSAs using HHblits or similar
        # For now, create minimal features
        features = self._create_minimal_features(sequence)
        
        import pickle
        with open(features_file, 'wb') as f:
            pickle.dump(features, f)
        
        input_files = {
            'fasta': fasta_file,
            'features': features_file
        }
        
        # Add ligand information if requested
        if include_ligands:
            ligand_file = input_dir / f"{fragment_id}_ligands.json"
            ligands = self._create_ligand_input()
            
            with open(ligand_file, 'w') as f:
                json.dump(ligands, f)
            
            input_files['ligands'] = ligand_file
        
        return input_files
    
    def _create_minimal_features(self, sequence: str) -> Dict:
        """Create minimal features for AF3 prediction.
        
        Args:
            sequence: Protein sequence
            
        Returns:
            Dictionary with minimal features
        """
        seq_len = len(sequence)
        
        features = {
            'aatype': np.array([self._aa_to_int(aa) for aa in sequence]),
            'residue_index': np.arange(seq_len),
            'seq_length': np.array([seq_len]),
            'sequence': sequence,
            'domain_name': 'IDR_fragment',
            
            # Minimal MSA (just the sequence itself)
            'msa': np.array([[self._aa_to_int(aa) for aa in sequence]]),
            'num_alignments': np.array([1]),
            'msa_species_identifiers': np.array([b'query']),
            
            # Dummy template features
            'template_aatype': np.zeros((1, seq_len), dtype=np.int32),
            'template_all_atom_positions': np.zeros((1, seq_len, 37, 3), dtype=np.float32),
            'template_all_atom_mask': np.zeros((1, seq_len, 37), dtype=np.float32),
            'template_sequence': np.array([b'']),
            'template_domain_names': np.array([b'']),
            'template_sum_probs': np.zeros((1,), dtype=np.float32),
            
            # Deletion matrix
            'deletion_matrix_int': np.zeros((1, seq_len), dtype=np.int32),
            
            # Cluster bias
            'cluster_bias_mask': np.ones((1,), dtype=np.float32),
            'bert_mask': np.ones((seq_len,), dtype=np.float32),
        }
        
        return features
    
    def _aa_to_int(self, aa: str) -> int:
        """Convert amino acid to integer."""
        aa_map = {
            'A': 0, 'R': 1, 'N': 2, 'D': 3, 'C': 4, 'Q': 5, 'E': 6, 'G': 7,
            'H': 8, 'I': 9, 'L': 10, 'K': 11, 'M': 12, 'F': 13, 'P': 14,
            'S': 15, 'T': 16, 'W': 17, 'Y': 18, 'V': 19, 'X': 20
        }
        return aa_map.get(aa, 20)
    
    def _create_ligand_input(self) -> Dict:
        """Create ligand input for multimer prediction."""
        # Simplified ligand definitions for RuBisCO
        ligands = {
            'CO2': {
                'smiles': 'O=C=O',
                'count': 1,
                'binding_sites': ['active_site']
            },
            'Mg2+': {
                'smiles': '[Mg+2]',
                'count': 1,
                'binding_sites': ['active_site']
            }
        }
        return ligands
    
    def run_alphafold3_prediction(self, input_files: Dict[str, Path], 
                                fragment_id: str) -> Optional[Path]:
        """Run AlphaFold3 prediction.
        
        Args:
            input_files: Dictionary with input file paths
            fragment_id: Fragment identifier
            
        Returns:
            Path to predicted structure or None if failed
        """
        if self.use_mock:
            return self._create_mock_prediction(input_files['fasta'], fragment_id)
        
        output_dir = self.temp_dir / fragment_id / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Construct AF3 command
        cmd = [
            'python', 'run_alphafold.py',
            '--fasta_paths', str(input_files['fasta']),
            '--model_preset', 'monomer',
            '--db_preset', 'reduced_dbs',
            '--output_dir', str(output_dir),
            '--max_template_date', '2024-01-01',
            '--num_multimer_predictions_per_model', str(self.af3_config['num_ensemble']),
            '--num_recycles', str(self.af3_config['num_recycles'])
        ]
        
        # Add ligand input if available
        if 'ligands' in input_files:
            cmd.extend(['--ligand_input', str(input_files['ligands'])])
        
        try:
            logger.info(f"Running AlphaFold3 prediction for {fragment_id}")
            
            # Run AF3
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=3600,  # 1 hour timeout
                cwd=self.model_dir
            )
            
            if result.returncode != 0:
                logger.error(f"AF3 prediction failed: {result.stderr}")
                return None
            
            # Find output structure
            predicted_structures = list(output_dir.glob("**/*relaxed*.pdb"))
            
            if not predicted_structures:
                logger.error("No predicted structures found")
                return None
            
            # Return the best ranked structure
            best_structure = sorted(predicted_structures)[0]
            logger.info(f"AF3 prediction completed: {best_structure}")
            
            return best_structure
            
        except subprocess.TimeoutExpired:
            logger.error(f"AF3 prediction timed out for {fragment_id}")
            return None
        
        except Exception as e:
            logger.error(f"Error running AF3 prediction: {e}")
            return None
    
    def _create_mock_prediction(self, fasta_file: Path, fragment_id: str) -> Path:
        """Create mock AF3 prediction for demonstration.
        
        Args:
            fasta_file: Input FASTA file
            fragment_id: Fragment identifier
            
        Returns:
            Path to mock predicted structure
        """
        logger.info(f"Creating mock AF3 prediction for {fragment_id}")
        
        # Read sequence
        sequence = str(SeqIO.read(fasta_file, "fasta").seq)
        
        # Generate mock coordinates
        mock_coords = self._generate_mock_coordinates(sequence)
        
        # Create PDB structure
        mock_structure = self._create_pdb_from_coordinates(mock_coords, sequence, fragment_id)
        
        # Save to file
        output_file = self.temp_dir / fragment_id / f"{fragment_id}_mock_af3.pdb"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.io.set_structure(mock_structure)
        self.io.save(str(output_file))
        
        return output_file
    
    def _generate_mock_coordinates(self, sequence: str) -> np.ndarray:
        """Generate mock coordinates for a sequence.
        
        Args:
            sequence: Protein sequence
            
        Returns:
            Mock coordinates array [N_residues, 4, 3] for N, CA, C, O atoms
        """
        n_residues = len(sequence)
        coords = np.zeros((n_residues, 4, 3))
        
        # Generate extended conformation with some disorder
        np.random.seed(hash(sequence) % 2**32)  # Reproducible randomness
        
        for i in range(n_residues):
            # Base position along extended chain
            base_x = i * 3.8  # Approximate CA-CA distance
            
            # Add disorder based on sequence properties
            disorder_factor = self._get_disorder_factor(sequence[i])
            
            # Random displacement
            displacement = np.random.normal(0, disorder_factor * 2.0, 3)
            
            # N atom
            coords[i, 0] = [base_x - 1.2, 0.0, 0.0] + displacement
            
            # CA atom
            coords[i, 1] = [base_x, 0.0, 0.0] + displacement
            
            # C atom
            coords[i, 2] = [base_x + 1.2, 0.0, 0.0] + displacement
            
            # O atom
            coords[i, 3] = [base_x + 1.5, 1.2, 0.0] + displacement
        
        return coords
    
    def _get_disorder_factor(self, aa: str) -> float:
        """Get disorder factor for amino acid."""
        disorder_factors = {
            'P': 3.0, 'G': 2.5, 'S': 2.0, 'T': 2.0, 'N': 2.0, 'Q': 2.0,
            'D': 1.8, 'E': 1.8, 'K': 1.8, 'R': 1.8, 'H': 1.5,
            'A': 1.2, 'V': 0.8, 'I': 0.6, 'L': 0.6, 'M': 0.8, 'F': 0.5,
            'Y': 0.5, 'W': 0.4, 'C': 0.7
        }
        return disorder_factors.get(aa, 1.0)
    
    def _create_pdb_from_coordinates(self, coords: np.ndarray, 
                                   sequence: str, structure_id: str) -> PDB.Structure.Structure:
        """Create PDB structure from coordinates.
        
        Args:
            coords: Coordinates array [N_residues, 4, 3]
            sequence: Protein sequence
            structure_id: Structure identifier
            
        Returns:
            PDB Structure object
        """
        structure = PDB.Structure.Structure(structure_id)
        model = PDB.Model.Model(0)
        structure.add(model)
        
        chain = PDB.Chain.Chain('A')
        model.add(chain)
        
        atom_names = ['N', 'CA', 'C', 'O']
        
        for i, aa in enumerate(sequence):
            residue = PDB.Residue.Residue((' ', i + 1, ' '), aa, ' ')
            chain.add(residue)
            
            for j, atom_name in enumerate(atom_names):
                atom = PDB.Atom.Atom(
                    atom_name,
                    coords[i, j],
                    1.0,  # B-factor
                    1.0,  # Occupancy
                    ' ',  # Alt loc
                    atom_name,
                    j + 1,  # Serial number
                    element=atom_name[0]
                )
                residue.add(atom)
        
        return structure
    
    def predict_idr_ensemble(self, sequence: str, fragment_id: str,
                           n_models: int = None) -> List[Path]:
        """Predict ensemble of structures for IDR fragment.
        
        Args:
            sequence: IDR sequence
            fragment_id: Fragment identifier
            n_models: Number of models to generate
            
        Returns:
            List of paths to predicted structures
        """
        if n_models is None:
            n_models = self.config.evaluation.ensemble_size
        
        logger.info(f"Predicting ensemble of {n_models} structures for {fragment_id}")
        
        predicted_structures = []
        
        for model_idx in range(n_models):
            model_id = f"{fragment_id}_model_{model_idx}"
            
            # Prepare input files
            input_files = self.prepare_input_files(sequence, model_id)
            
            # Run prediction
            predicted_structure = self.run_alphafold3_prediction(input_files, model_id)
            
            if predicted_structure is not None:
                predicted_structures.append(predicted_structure)
        
        logger.info(f"Generated {len(predicted_structures)} structures for {fragment_id}")
        return predicted_structures
    
    def extract_confidence_scores(self, predicted_structure: Path) -> Dict[str, float]:
        """Extract confidence scores from AF3 prediction.
        
        Args:
            predicted_structure: Path to predicted PDB file
            
        Returns:
            Dictionary with confidence metrics
        """
        structure = self.parser.get_structure('predicted', predicted_structure)
        
        confidence_scores = {
            'mean_plddt': 0.0,
            'min_plddt': 100.0,
            'max_plddt': 0.0,
            'low_confidence_fraction': 0.0
        }
        
        plddt_scores = []
        
        for model in structure:
            for chain in model:
                for residue in chain:
                    if residue.get_id()[0] == ' ':  # Standard residue
                        for atom in residue:
                            if atom.get_name() == 'CA':
                                # B-factor contains pLDDT in AF predictions
                                plddt = atom.get_bfactor()
                                plddt_scores.append(plddt)
        
        if plddt_scores:
            confidence_scores['mean_plddt'] = np.mean(plddt_scores)
            confidence_scores['min_plddt'] = np.min(plddt_scores)
            confidence_scores['max_plddt'] = np.max(plddt_scores)
            
            # Fraction with low confidence (< threshold)
            low_conf_count = sum(1 for score in plddt_scores 
                               if score < self.af3_config['confidence_threshold'])
            confidence_scores['low_confidence_fraction'] = low_conf_count / len(plddt_scores)
        
        return confidence_scores
    
    def evaluate_predictions(self, predicted_structures: List[Path],
                           reference_structure: Optional[Path] = None) -> Dict:
        """Evaluate AF3 predictions.
        
        Args:
            predicted_structures: List of predicted structure files
            reference_structure: Reference structure for comparison
            
        Returns:
            Dictionary with evaluation results
        """
        logger.info("Evaluating AF3 predictions...")
        
        results = {
            'n_predictions': len(predicted_structures),
            'confidence_scores': [],
            'structural_metrics': {},
            'ensemble_metrics': {}
        }
        
        # Extract confidence scores
        for pred_file in predicted_structures:
            conf_scores = self.extract_confidence_scores(pred_file)
            results['confidence_scores'].append(conf_scores)
        
        # Calculate ensemble metrics
        if len(predicted_structures) > 1:
            ensemble_metrics = self.metrics.calculate_ensemble_metrics(predicted_structures)
            results['ensemble_metrics'] = ensemble_metrics
        
        # Compare to reference if available
        if reference_structure is not None:
            structural_metrics = []
            
            for pred_file in predicted_structures:
                metrics = self.metrics.calculate_structural_metrics(
                    pred_file, reference_structure
                )
                structural_metrics.append(metrics)
            
            # Average metrics
            if structural_metrics:
                avg_metrics = {}
                for key in structural_metrics[0].keys():
                    values = [m[key] for m in structural_metrics if key in m]
                    if values:
                        avg_metrics[f'mean_{key}'] = np.mean(values)
                        avg_metrics[f'std_{key}'] = np.std(values)
                
                results['structural_metrics'] = avg_metrics
        
        return results
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary files")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
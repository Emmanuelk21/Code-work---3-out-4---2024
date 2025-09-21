"""
Basic functionality tests for the QML vs CML IDR prediction project.
"""

import unittest
import numpy as np
import tempfile
import os
from pathlib import Path

# Add project root to path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from data.preprocessing import PDBbindProcessor
from classical.alphafold_baseline import AlphaFoldPredictor
from quantum.vqe_framework import VQEPredictor, QuantumConfig
from evaluation.metrics import ComparativeEvaluator


class TestDataPreprocessing(unittest.TestCase):
    """Test data preprocessing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = PDBbindProcessor()
    
    def test_processor_initialization(self):
        """Test processor initialization."""
        self.assertIsNotNone(self.processor)
        self.assertIsNotNone(self.processor.parser)
    
    def test_mock_fragment_creation(self):
        """Test creation of mock fragments."""
        # Create a simple mock fragment
        mock_fragment = {
            'pdb_id': 'TEST',
            'chain_id': 'A',
            'start_residue': 1,
            'end_residue': 10,
            'sequence': 'ACDEFGHIKL',
            'length': 10,
            'coordinates': np.random.randn(10, 3),
            'dihedral_angles': np.random.uniform(-np.pi, np.pi, 9),
            'disorder_scores': [0.7] * 10,
            'qubit_count': 20,
            'structure_file': 'test.pdb'
        }
        
        self.assertEqual(mock_fragment['length'], 10)
        self.assertEqual(len(mock_fragment['sequence']), 10)
        self.assertEqual(mock_fragment['coordinates'].shape, (10, 3))
    
    def test_fragment_save_load(self):
        """Test saving and loading fragments."""
        # Create mock fragments
        mock_fragments = []
        for i in range(3):
            fragment = {
                'pdb_id': f'TEST{i}',
                'chain_id': 'A',
                'start_residue': 1,
                'end_residue': 10,
                'sequence': 'ACDEFGHIKL',
                'length': 10,
                'coordinates': np.random.randn(10, 3),
                'dihedral_angles': np.random.uniform(-np.pi, np.pi, 9),
                'disorder_scores': [0.7] * 10,
                'qubit_count': 20,
                'structure_file': f'test{i}.pdb'
            }
            mock_fragments.append(fragment)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.h5', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            self.processor.save_fragments(mock_fragments, tmp_path)
            
            # Load fragments
            loaded_fragments = self.processor.load_fragments(tmp_path)
            
            # Verify
            self.assertEqual(len(loaded_fragments), 3)
            self.assertEqual(loaded_fragments[0]['pdb_id'], 'TEST0')
            self.assertEqual(loaded_fragments[1]['pdb_id'], 'TEST1')
            self.assertEqual(loaded_fragments[2]['pdb_id'], 'TEST2')
            
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestClassicalML(unittest.TestCase):
    """Test classical ML functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.predictor = AlphaFoldPredictor()
    
    def test_predictor_initialization(self):
        """Test predictor initialization."""
        self.assertIsNotNone(self.predictor)
        self.assertIsNotNone(self.predictor.parser)
    
    def test_mock_structure_generation(self):
        """Test mock structure generation."""
        sequence = "ACDEFGHIKL"
        mock_pdb = "test_output.pdb"
        
        # This should not raise an exception
        self.predictor._generate_mock_structure(sequence, Path(mock_pdb), 0)
        
        # Clean up
        if os.path.exists(mock_pdb):
            os.unlink(mock_pdb)
    
    def test_energy_calculation(self):
        """Test energy calculation."""
        coordinates = np.random.randn(5, 3)
        energy = self.predictor._estimate_energy(coordinates)
        
        self.assertIsInstance(energy, float)
        self.assertGreaterEqual(energy, 0)


class TestQuantumML(unittest.TestCase):
    """Test quantum ML functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = QuantumConfig(noise_level=0.0, ansatz_depth=3)
        self.predictor = VQEPredictor(self.config)
    
    def test_config_initialization(self):
        """Test quantum configuration."""
        self.assertEqual(self.config.noise_level, 0.0)
        self.assertEqual(self.config.ansatz_depth, 3)
        self.assertEqual(self.config.optimizer, "COBYLA")
    
    def test_predictor_initialization(self):
        """Test predictor initialization."""
        self.assertIsNotNone(self.predictor)
        self.assertIsNotNone(self.predictor.config)
    
    def test_hamiltonian_construction(self):
        """Test Hamiltonian construction."""
        coordinates = np.random.randn(5, 3)
        sequence = "ACDEF"
        
        from quantum.vqe_framework import ProteinHamiltonian
        hamiltonian_builder = ProteinHamiltonian(coordinates, sequence)
        hamiltonian = hamiltonian_builder.build_ising_hamiltonian()
        
        self.assertIsNotNone(hamiltonian)
        self.assertGreater(hamiltonian.num_qubits, 0)
    
    def test_ansatz_construction(self):
        """Test ansatz construction."""
        from quantum.vqe_framework import HardwareEfficientAnsatz
        
        ansatz_builder = HardwareEfficientAnsatz(num_qubits=4, depth=3)
        circuit = ansatz_builder.build_circuit()
        
        self.assertIsNotNone(circuit)
        self.assertEqual(circuit.num_qubits, 4)


class TestEvaluation(unittest.TestCase):
    """Test evaluation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = ComparativeEvaluator()
    
    def test_evaluator_initialization(self):
        """Test evaluator initialization."""
        self.assertIsNotNone(self.evaluator)
        self.assertIsNotNone(self.evaluator.structure_metrics)
        self.assertIsNotNone(self.evaluator.energy_metrics)
        self.assertIsNotNone(self.evaluator.ensemble_metrics)
    
    def test_rmsd_calculation(self):
        """Test RMSD calculation."""
        coords1 = np.random.randn(5, 3)
        coords2 = coords1 + np.random.randn(5, 3) * 0.1
        
        rmsd = self.evaluator.structure_metrics.calculate_rmsd(coords1, coords2)
        
        self.assertIsInstance(rmsd, float)
        self.assertGreaterEqual(rmsd, 0)
    
    def test_radius_of_gyration(self):
        """Test radius of gyration calculation."""
        coordinates = np.random.randn(10, 3)
        rg = self.evaluator.structure_metrics.calculate_radius_of_gyration(coordinates)
        
        self.assertIsInstance(rg, float)
        self.assertGreaterEqual(rg, 0)
    
    def test_energy_metrics(self):
        """Test energy metrics calculation."""
        coordinates = np.random.randn(5, 3)
        atom_types = ['C'] * 5
        charges = [0.0] * 5
        
        energy = self.evaluator.energy_metrics.calculate_total_energy(
            coordinates, atom_types, charges
        )
        
        self.assertIsInstance(energy, float)


class TestIntegration(unittest.TestCase):
    """Test integration between components."""
    
    def test_end_to_end_workflow(self):
        """Test basic end-to-end workflow."""
        # Create mock data
        mock_fragments = []
        for i in range(2):
            fragment = {
                'pdb_id': f'TEST{i}',
                'chain_id': 'A',
                'start_residue': 1,
                'end_residue': 10,
                'sequence': 'ACDEFGHIKL',
                'length': 10,
                'coordinates': np.random.randn(10, 3),
                'dihedral_angles': np.random.uniform(-np.pi, np.pi, 9),
                'disorder_scores': [0.7] * 10,
                'qubit_count': 20,
                'structure_file': f'test{i}.pdb'
            }
            mock_fragments.append(fragment)
        
        # Test classical prediction
        classical_predictor = AlphaFoldPredictor()
        classical_predictions = classical_predictor.predict_idr_ensemble(mock_fragments)
        
        self.assertEqual(len(classical_predictions), 2)
        self.assertIn('pdb_id', classical_predictions[0])
        self.assertIn('sequence', classical_predictions[0])
        
        # Test quantum prediction
        quantum_config = QuantumConfig(noise_level=0.0, ansatz_depth=3)
        quantum_predictor = VQEPredictor(quantum_config)
        quantum_predictions = quantum_predictor.predict_idr_ensemble(mock_fragments, [quantum_config])
        
        self.assertGreater(len(quantum_predictions), 0)
        self.assertIn('pdb_id', quantum_predictions[0])
        self.assertIn('optimal_energy', quantum_predictions[0])


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
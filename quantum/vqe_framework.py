"""
VQE-based Quantum Machine Learning framework for IDR prediction.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import logging
from dataclasses import dataclass

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit import transpile, execute
from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp
from qiskit.primitives import Estimator
from qiskit_aer import AerSimulator
from qiskit_algorithms import VQE, NumPyMinimumEigensolver
from qiskit_algorithms.optimizers import COBYLA, SPSA, L_BFGS_B
from qiskit_algorithms.utils import algorithm_globals

from config.settings import (
    QISKIT_BACKEND, SHOTS, NOISE_LEVELS, ANSATZ_DEPTHS,
    MAX_QUBITS_PER_RESIDUE, RESULTS_DIR
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QuantumConfig:
    """Configuration for quantum simulations."""
    backend: str = QISKIT_BACKEND
    shots: int = SHOTS
    noise_level: float = 0.0
    ansatz_depth: int = 5
    optimizer: str = "COBYLA"
    max_iterations: int = 500
    convergence_tolerance: float = 1e-4


class ProteinHamiltonian:
    """Constructs quantum Hamiltonians for protein folding problems."""
    
    def __init__(self, coordinates: np.ndarray, sequence: str):
        self.coordinates = coordinates
        self.sequence = sequence
        self.num_residues = len(sequence)
        self.num_qubits = min(self.num_residues * MAX_QUBITS_PER_RESIDUE, 30)
        
    def build_ising_hamiltonian(self) -> SparsePauliOp:
        """Build Ising-like Hamiltonian for protein folding."""
        logger.info(f"Building Ising Hamiltonian for {self.num_residues} residues")
        
        # Initialize Hamiltonian terms
        pauli_terms = []
        coefficients = []
        
        # Local field terms (h_i * Z_i)
        for i in range(self.num_qubits):
            # Local energy based on residue properties
            h_i = self._calculate_local_energy(i)
            if abs(h_i) > 1e-6:
                pauli_string = "I" * i + "Z" + "I" * (self.num_qubits - i - 1)
                pauli_terms.append(pauli_string)
                coefficients.append(h_i)
        
        # Interaction terms (J_ij * Z_i * Z_j)
        for i in range(self.num_qubits):
            for j in range(i + 1, self.num_qubits):
                # Interaction energy based on pairwise distances
                j_ij = self._calculate_interaction_energy(i, j)
                if abs(j_ij) > 1e-6:
                    pauli_string = "I" * i + "Z" + "I" * (j - i - 1) + "Z" + "I" * (self.num_qubits - j - 1)
                    pauli_terms.append(pauli_string)
                    coefficients.append(j_ij)
        
        # Create SparsePauliOp
        if pauli_terms:
            hamiltonian = SparsePauliOp(pauli_terms, coefficients)
        else:
            # Fallback to simple Hamiltonian
            hamiltonian = self._create_simple_hamiltonian()
        
        return hamiltonian
    
    def _calculate_local_energy(self, qubit_idx: int) -> float:
        """Calculate local energy for a qubit."""
        residue_idx = qubit_idx // MAX_QUBITS_PER_RESIDUE
        
        if residue_idx >= len(self.sequence):
            return 0.0
        
        # Energy based on amino acid properties
        aa = self.sequence[residue_idx]
        
        # Hydrophobicity-based energy
        hydrophobic_aas = {'A', 'V', 'L', 'I', 'M', 'F', 'Y', 'W'}
        if aa in hydrophobic_aas:
            return -0.5  # Favorable for buried positions
        else:
            return 0.2   # Less favorable for exposed positions
    
    def _calculate_interaction_energy(self, qubit_i: int, qubit_j: int) -> float:
        """Calculate interaction energy between two qubits."""
        residue_i = qubit_i // MAX_QUBITS_PER_RESIDUE
        residue_j = qubit_j // MAX_QUBITS_PER_RESIDUE
        
        if residue_i >= len(self.coordinates) or residue_j >= len(self.coordinates):
            return 0.0
        
        # Calculate distance between residues
        dist = np.linalg.norm(self.coordinates[residue_i] - self.coordinates[residue_j])
        
        # Interaction energy based on distance
        if dist < 4.0:  # Close contact
            return -0.3  # Attractive
        elif dist < 8.0:  # Medium range
            return -0.1  # Weak attraction
        else:
            return 0.0   # No interaction
    
    def _create_simple_hamiltonian(self) -> SparsePauliOp:
        """Create a simple Hamiltonian as fallback."""
        logger.warning("Using simple Hamiltonian fallback")
        
        # Simple antiferromagnetic chain
        pauli_terms = []
        coefficients = []
        
        for i in range(self.num_qubits - 1):
            pauli_string = "I" * i + "Z" + "I" * (self.num_qubits - i - 2) + "Z"
            pauli_terms.append(pauli_string)
            coefficients.append(-1.0)
        
        return SparsePauliOp(pauli_terms, coefficients)


class HardwareEfficientAnsatz:
    """Hardware-efficient ansatz for VQE."""
    
    def __init__(self, num_qubits: int, depth: int = 5):
        self.num_qubits = num_qubits
        self.depth = depth
        self.parameters = []
        
    def build_circuit(self) -> QuantumCircuit:
        """Build the hardware-efficient ansatz circuit."""
        qr = QuantumRegister(self.num_qubits, 'q')
        cr = ClassicalRegister(self.num_qubits, 'c')
        qc = QuantumCircuit(qr, cr)
        
        # Initial state preparation (angle embedding)
        for i in range(self.num_qubits):
            param = Parameter(f'θ_{i}')
            self.parameters.append(param)
            qc.ry(param, qr[i])
        
        # Entangling layers
        for layer in range(self.depth):
            # Entangling gates (linear topology)
            for i in range(self.num_qubits - 1):
                qc.cx(qr[i], qr[i + 1])
            
            # Rotation gates
            for i in range(self.num_qubits):
                param_ry = Parameter(f'θ_ry_{layer}_{i}')
                param_rz = Parameter(f'θ_rz_{layer}_{i}')
                self.parameters.append(param_ry)
                self.parameters.append(param_rz)
                qc.ry(param_ry, qr[i])
                qc.rz(param_rz, qr[i])
        
        return qc
    
    def get_parameters(self) -> List[Parameter]:
        """Get list of parameters."""
        return self.parameters


class VQEPredictor:
    """VQE-based predictor for IDR structures."""
    
    def __init__(self, config: Optional[QuantumConfig] = None):
        self.config = config or QuantumConfig()
        self.results_dir = RESULTS_DIR / "quantum"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Set random seed for reproducibility
        algorithm_globals.random_seed = 42
        
        # Initialize backend
        self._setup_backend()
    
    def _setup_backend(self):
        """Setup quantum backend."""
        logger.info(f"Setting up quantum backend: {self.config.backend}")
        
        if self.config.backend == "qasm_simulator":
            self.backend = AerSimulator()
        elif self.config.backend == "statevector_simulator":
            self.backend = AerSimulator(method='statevector')
        else:
            self.backend = AerSimulator()
        
        # Add noise if specified
        if self.config.noise_level > 0:
            from qiskit_aer.noise import NoiseModel, depolarizing_error
            noise_model = NoiseModel()
            error = depolarizing_error(self.config.noise_level, 1)
            noise_model.add_all_qubit_quantum_error(error, ['ry', 'rz', 'cx'])
            self.backend.set_options(noise_model=noise_model)
    
    def predict_structure(self, coordinates: np.ndarray, sequence: str, 
                         pdb_id: str) -> Dict:
        """Predict IDR structure using VQE."""
        logger.info(f"Predicting structure for {pdb_id} (length: {len(sequence)})")
        
        # Build Hamiltonian
        hamiltonian_builder = ProteinHamiltonian(coordinates, sequence)
        hamiltonian = hamiltonian_builder.build_ising_hamiltonian()
        
        # Build ansatz
        ansatz_builder = HardwareEfficientAnsatz(
            hamiltonian_builder.num_qubits, 
            self.config.ansatz_depth
        )
        ansatz = ansatz_builder.build_circuit()
        
        # Setup optimizer
        optimizer = self._get_optimizer()
        
        # Run VQE
        vqe_result = self._run_vqe(hamiltonian, ansatz, optimizer)
        
        # Post-process results
        result = self._post_process_vqe_result(
            vqe_result, hamiltonian_builder, ansatz, pdb_id, sequence
        )
        
        return result
    
    def _get_optimizer(self):
        """Get optimizer based on configuration."""
        if self.config.optimizer == "COBYLA":
            return COBYLA(maxiter=self.config.max_iterations)
        elif self.config.optimizer == "SPSA":
            return SPSA(maxiter=self.config.max_iterations)
        elif self.config.optimizer == "L_BFGS_B":
            return L_BFGS_B(maxiter=self.config.max_iterations)
        else:
            return COBYLA(maxiter=self.config.max_iterations)
    
    def _run_vqe(self, hamiltonian: SparsePauliOp, ansatz: QuantumCircuit, 
                 optimizer) -> Dict:
        """Run VQE algorithm."""
        logger.info("Running VQE optimization...")
        
        # Initialize estimator
        estimator = Estimator()
        
        # Create VQE instance
        vqe = VQE(
            estimator=estimator,
            ansatz=ansatz,
            optimizer=optimizer,
            initial_point=np.random.random(len(ansatz.parameters)) * 2 * np.pi
        )
        
        # Run VQE
        result = vqe.compute_minimum_eigenvalue(hamiltonian)
        
        return result
    
    def _post_process_vqe_result(self, vqe_result: Dict, hamiltonian_builder: ProteinHamiltonian,
                                ansatz: QuantumCircuit, pdb_id: str, sequence: str) -> Dict:
        """Post-process VQE results."""
        logger.info("Post-processing VQE results...")
        
        # Get optimal parameters
        optimal_params = vqe_result.optimal_parameters
        
        # Create circuit with optimal parameters
        optimal_circuit = ansatz.bind_parameters(optimal_params)
        
        # Measure expectation values
        expectation_values = self._measure_expectation_values(optimal_circuit, hamiltonian_builder)
        
        # Decode to coordinates
        predicted_coords = self._decode_to_coordinates(expectation_values, hamiltonian_builder)
        
        # Calculate metrics
        metrics = self._calculate_quantum_metrics(predicted_coords, sequence)
        
        result = {
            'pdb_id': pdb_id,
            'sequence': sequence,
            'optimal_energy': vqe_result.eigenvalue,
            'optimal_parameters': optimal_params,
            'predicted_coordinates': predicted_coords,
            'expectation_values': expectation_values,
            'metrics': metrics,
            'convergence_info': {
                'num_iterations': vqe_result.cost_function_evals,
                'converged': vqe_result.optimizer_result.success
            }
        }
        
        return result
    
    def _measure_expectation_values(self, circuit: QuantumCircuit, 
                                   hamiltonian_builder: ProteinHamiltonian) -> np.ndarray:
        """Measure expectation values of Pauli-Z operators."""
        # Add measurement gates
        measured_circuit = circuit.copy()
        measured_circuit.measure_all()
        
        # Execute circuit
        job = execute(measured_circuit, self.backend, shots=self.config.shots)
        result = job.result()
        counts = result.get_counts()
        
        # Calculate expectation values
        expectation_values = np.zeros(hamiltonian_builder.num_qubits)
        
        for bitstring, count in counts.items():
            probability = count / self.config.shots
            
            # Convert bitstring to expectation values
            for i, bit in enumerate(reversed(bitstring)):
                if i < hamiltonian_builder.num_qubits:
                    expectation_values[i] += probability * (1 if bit == '0' else -1)
        
        return expectation_values
    
    def _decode_to_coordinates(self, expectation_values: np.ndarray, 
                              hamiltonian_builder: ProteinHamiltonian) -> np.ndarray:
        """Decode expectation values to 3D coordinates."""
        num_residues = hamiltonian_builder.num_residues
        coordinates = np.zeros((num_residues, 3))
        
        # Simple decoding: map expectation values to coordinates
        for i in range(num_residues):
            # Get expectation values for this residue
            start_idx = i * MAX_QUBITS_PER_RESIDUE
            end_idx = min(start_idx + MAX_QUBITS_PER_RESIDUE, len(expectation_values))
            residue_expectations = expectation_values[start_idx:end_idx]
            
            # Map to 3D coordinates (simplified)
            x = i * 3.8 + np.mean(residue_expectations) * 2.0
            y = np.sin(i * 0.5) * 3.0 + residue_expectations[0] if len(residue_expectations) > 0 else 0.0
            z = np.cos(i * 0.3) * 2.0 + residue_expectations[1] if len(residue_expectations) > 1 else 0.0
            
            coordinates[i] = [x, y, z]
        
        return coordinates
    
    def _calculate_quantum_metrics(self, coordinates: np.ndarray, sequence: str) -> Dict:
        """Calculate quantum-specific metrics."""
        if len(coordinates) == 0:
            return {}
        
        # Radius of gyration
        center = np.mean(coordinates, axis=0)
        distances = np.linalg.norm(coordinates - center, axis=1)
        rg = np.sqrt(np.mean(distances**2))
        
        # End-to-end distance
        end_to_end = np.linalg.norm(coordinates[-1] - coordinates[0])
        
        # Compactness (inverse of radius of gyration)
        compactness = 1.0 / (rg + 1e-6)
        
        return {
            'radius_of_gyration': rg,
            'end_to_end_distance': end_to_end,
            'compactness': compactness,
            'num_residues': len(sequence)
        }
    
    def predict_idr_ensemble(self, idr_fragments: List[Dict], 
                           configs: Optional[List[QuantumConfig]] = None) -> List[Dict]:
        """Predict structures for a list of IDR fragments with different configurations."""
        logger.info(f"Predicting structures for {len(idr_fragments)} IDR fragments")
        
        if configs is None:
            configs = [self.config]
        
        all_predictions = []
        
        for fragment in idr_fragments:
            logger.info(f"Processing fragment: {fragment['pdb_id']} {fragment['chain_id']}")
            
            fragment_predictions = []
            
            for config in configs:
                # Update configuration
                original_config = self.config
                self.config = config
                self._setup_backend()
                
                # Predict structure
                prediction = self.predict_structure(
                    fragment['coordinates'],
                    fragment['sequence'],
                    f"{fragment['pdb_id']}_{fragment['chain_id']}"
                )
                
                # Add configuration info
                prediction['config'] = {
                    'noise_level': config.noise_level,
                    'ansatz_depth': config.ansatz_depth,
                    'optimizer': config.optimizer
                }
                
                # Add fragment metadata
                prediction['fragment_info'] = fragment
                
                fragment_predictions.append(prediction)
                
                # Restore original configuration
                self.config = original_config
                self._setup_backend()
            
            all_predictions.extend(fragment_predictions)
        
        return all_predictions
    
    def save_predictions(self, predictions: List[Dict], output_file: str):
        """Save quantum predictions to file."""
        logger.info(f"Saving {len(predictions)} quantum predictions to {output_file}")
        
        # Convert to DataFrame for easier handling
        data = []
        for pred in predictions:
            row = {
                'pdb_id': pred['pdb_id'],
                'sequence': pred['sequence'],
                'optimal_energy': pred['optimal_energy'],
                'radius_of_gyration': pred['metrics'].get('radius_of_gyration', 0.0),
                'end_to_end_distance': pred['metrics'].get('end_to_end_distance', 0.0),
                'compactness': pred['metrics'].get('compactness', 0.0),
                'converged': pred['convergence_info']['converged'],
                'num_iterations': pred['convergence_info']['num_iterations'],
                'noise_level': pred['config']['noise_level'],
                'ansatz_depth': pred['config']['ansatz_depth'],
                'optimizer': pred['config']['optimizer']
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        df.to_csv(output_file, index=False)
        
        logger.info(f"Quantum predictions saved to {output_file}")


def main():
    """Example usage of VQE predictor."""
    from data.preprocessing import PDBbindProcessor
    
    # Load IDR fragments
    processor = PDBbindProcessor()
    fragments = processor.load_fragments("data/rubisco_idr_fragments.h5")
    
    # Create different configurations for ensemble
    configs = [
        QuantumConfig(noise_level=0.0, ansatz_depth=3, optimizer="COBYLA"),
        QuantumConfig(noise_level=0.01, ansatz_depth=5, optimizer="SPSA"),
        QuantumConfig(noise_level=0.05, ansatz_depth=7, optimizer="L_BFGS_B")
    ]
    
    # Initialize predictor
    predictor = VQEPredictor()
    
    # Predict structures
    predictions = predictor.predict_idr_ensemble(fragments[:3], configs)  # Test with first 3
    
    # Save results
    predictor.save_predictions(predictions, "results/quantum_predictions.csv")
    
    logger.info("Quantum prediction complete!")


if __name__ == "__main__":
    main()
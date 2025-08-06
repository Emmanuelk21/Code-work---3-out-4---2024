# Quantum-Enhanced Blockchain for FAIR and CARE-Compliant DSI Benefit Allocation

## Overview

This system implements a quantum-enhanced blockchain platform for transparent, equitable Digital Sequence Information (DSI) governance under the CBD Cali Fund. It integrates Hyperledger Fabric blockchain technology with quantum computing attribution models and quorum sensing-inspired governance to ensure FAIR (Findable, Accessible, Interoperable, Reusable) and CARE (Collective benefit, Authority to control, Responsibility, Ethics) compliance.

## Architecture

### Core Components

1. **Hyperledger Fabric Blockchain**
   - Permissioned blockchain for secure DSI transaction recording
   - Smart contracts for automated benefit-sharing allocation
   - FAIR-compliant metadata integration with JSON-LD

2. **Quantum Attribution Layer (Qiskit)**
   - Quantum circuits for modeling complex DSI contributions
   - Probabilistic weight assignment for fair benefit allocation
   - Handles non-linear, interconnected contribution patterns

3. **Quorum Sensing Governance**
   - Decentralized decision-making protocols
   - IPLC stakeholder voting mechanisms
   - 60% quorum threshold for approvals

4. **FAIR-CARE Metadata System**
   - Digital Object Identifier (DOI) integration
   - Indigenous consent mechanisms
   - Standardized metadata schemas

## Key Features

- **Transparent DSI Tracking**: Immutable blockchain records of all DSI usage
- **Quantum Attribution**: Advanced modeling of multi-dataset contributions
- **Indigenous Rights Protection**: CARE-compliant governance ensuring IPLC authority
- **Automated Benefit-Sharing**: Smart contracts triggering payments to Cali Fund
- **FAIR Compliance**: Standardized, interoperable metadata
- **Permissioned Access**: Controlled access aligned with stakeholder rights

## Installation

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Node.js 16+ (for Hyperledger Fabric)
- IBM Quantum Experience account (optional, for real quantum hardware)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd quantum-blockchain-dsi
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Hyperledger Fabric network:
```bash
cd blockchain
./setup-fabric-network.sh
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize the system:
```bash
python scripts/initialize_system.py
```

## Usage

### Starting the System

```bash
# Start blockchain network
cd blockchain && ./start-network.sh

# Start quantum attribution service
python quantum/quantum_service.py

# Start governance service
python governance/governance_service.py

# Start web interface
python app.py
```

### DSI Registration

```python
from metadata.dsi_manager import DSIManager

dsi_manager = DSIManager()
dsi_data = {
    "sequence_id": "NC_045512.2",
    "source_community": "Indigenous Community XYZ",
    "access_terms": "Prior informed consent required",
    "benefit_sharing_percentage": 0.01
}
dsi_manager.register_dsi(dsi_data)
```

### Quantum Attribution

```python
from quantum.attribution_engine import QuantumAttributionEngine

engine = QuantumAttributionEngine()
contributions = engine.calculate_contributions([
    "dataset_1", "dataset_2", "dataset_3"
])
print(f"Attribution weights: {contributions}")
```

### Governance Voting

```python
from governance.quorum_system import QuorumGovernance

governance = QuorumGovernance()
proposal = {
    "type": "benefit_sharing_approval",
    "dataset_id": "NC_045512.2",
    "terms": "1% revenue share"
}
result = governance.submit_proposal(proposal)
```

## API Documentation

### DSI Management API

- `POST /api/dsi/register` - Register new DSI dataset
- `GET /api/dsi/{id}` - Retrieve DSI metadata
- `PUT /api/dsi/{id}/consent` - Update consent status

### Quantum Attribution API

- `POST /api/quantum/attribute` - Calculate quantum attribution
- `GET /api/quantum/results/{job_id}` - Get attribution results

### Governance API

- `POST /api/governance/proposal` - Submit governance proposal
- `POST /api/governance/vote` - Cast vote on proposal
- `GET /api/governance/status/{proposal_id}` - Check proposal status

## Testing

Run the test suite:

```bash
pytest tests/
```

Run specific test categories:

```bash
# Test blockchain functionality
pytest tests/test_blockchain.py

# Test quantum attribution
pytest tests/test_quantum.py

# Test governance
pytest tests/test_governance.py
```

## Configuration

### Environment Variables

- `FABRIC_NETWORK_PATH`: Path to Hyperledger Fabric network configuration
- `QUANTUM_BACKEND`: Quantum computing backend (simulator/ibm_quantum)
- `GOVERNANCE_QUORUM_THRESHOLD`: Voting quorum threshold (default: 0.6)
- `DSI_DATABASE_URL`: Database connection string

### Smart Contract Configuration

Smart contracts are deployed automatically during network setup. Configuration parameters can be modified in `blockchain/contracts/config/`.

## Contributing

1. Follow FAIR and CARE principles in all development
2. Ensure Indigenous stakeholder perspectives are incorporated
3. Run tests and linting before submitting PRs
4. Update documentation for any API changes

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Convention on Biological Diversity (CBD)
- Indigenous Peoples and Local Communities (IPLCs)
- FAIR and CARE principles communities
- Qiskit and Hyperledger Fabric development teams

## References

- Carroll, S. R., et al. (2021). Operationalizing the CARE and FAIR principles for Indigenous data futures.
- Scholz, A. H., et al. (2022). Multilateral benefit-sharing from digital sequence information.
- Convention on Biological Diversity. (2024). The operationalization of the multilateral mechanism on DSI.
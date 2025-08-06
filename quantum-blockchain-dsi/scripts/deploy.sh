#!/bin/bash

# Quantum-Enhanced Blockchain DSI System Deployment Script
# This script automates the deployment of the complete DSI governance system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_ENV="${1:-development}"
DOCKER_COMPOSE_FILE="docker-compose.yml"

echo -e "${BLUE}🚀 Starting Quantum-Enhanced DSI System Deployment${NC}"
echo -e "${BLUE}Environment: ${DEPLOYMENT_ENV}${NC}"
echo -e "${BLUE}Project Root: ${PROJECT_ROOT}${NC}"
echo "================================================================"

# Function to print status messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is required but not installed"
        exit 1
    fi
    
    # Check Docker (if using containers)
    if [ "$DEPLOYMENT_ENV" = "production" ]; then
        if ! command -v docker &> /dev/null; then
            print_error "Docker is required for production deployment"
            exit 1
        fi
        
        if ! command -v docker-compose &> /dev/null; then
            print_error "Docker Compose is required for production deployment"
            exit 1
        fi
    fi
    
    # Check Node.js (for Hyperledger Fabric)
    if ! command -v node &> /dev/null; then
        print_warning "Node.js not found. Hyperledger Fabric setup may require it."
    fi
    
    print_status "Prerequisites check completed ✅"
}

# Setup Python environment
setup_python_environment() {
    print_status "Setting up Python environment..."
    
    cd "$PROJECT_ROOT"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    print_status "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    print_status "Python environment setup completed ✅"
}

# Setup configuration
setup_configuration() {
    print_status "Setting up configuration..."
    
    cd "$PROJECT_ROOT"
    
    # Copy environment file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your specific configuration"
    fi
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p data
    mkdir -p backups
    mkdir -p blockchain/network
    
    print_status "Configuration setup completed ✅"
}

# Setup Hyperledger Fabric network
setup_fabric_network() {
    print_status "Setting up Hyperledger Fabric network..."
    
    cd "$PROJECT_ROOT/blockchain"
    
    # Check if fabric-samples exist
    if [ ! -d "fabric-samples" ]; then
        print_status "Downloading Hyperledger Fabric samples..."
        curl -sSL https://bit.ly/2ysbOFE | bash -s -- 2.5.0 1.5.2
    fi
    
    # Start the test network
    print_status "Starting Fabric test network..."
    cd fabric-samples/test-network
    ./network.sh up createChannel -c dsi-channel -ca
    
    # Deploy chaincode
    print_status "Deploying DSI chaincode..."
    ./network.sh deployCC -ccn dsi-chaincode -ccp ../../contracts -ccl go
    
    cd "$PROJECT_ROOT"
    print_status "Hyperledger Fabric network setup completed ✅"
}

# Initialize databases
initialize_databases() {
    print_status "Initializing databases..."
    
    cd "$PROJECT_ROOT"
    source venv/bin/activate
    
    # Initialize metadata database
    python -c "
from metadata.dsi_manager import DSIMetadataManager
manager = DSIMetadataManager()
print('Metadata database initialized')
"
    
    # Initialize governance system
    python -c "
from governance.quorum_system import QuorumGovernance
governance = QuorumGovernance()
print('Governance system initialized')
"
    
    print_status "Database initialization completed ✅"
}

# Run tests
run_tests() {
    print_status "Running integration tests..."
    
    cd "$PROJECT_ROOT"
    source venv/bin/activate
    
    # Run tests
    python -m pytest tests/ -v --tb=short
    
    # Run integration tests
    python tests/test_integration.py
    
    print_status "Tests completed successfully ✅"
}

# Start services (development)
start_development_services() {
    print_status "Starting development services..."
    
    cd "$PROJECT_ROOT"
    source venv/bin/activate
    
    # Start Redis (if available)
    if command -v redis-server &> /dev/null; then
        print_status "Starting Redis server..."
        redis-server --daemonize yes
    fi
    
    # Start the Flask application
    print_status "Starting Flask application..."
    export FLASK_ENV=development
    export FLASK_DEBUG=true
    nohup python app.py > logs/app.log 2>&1 &
    echo $! > app.pid
    
    print_status "Development services started ✅"
    print_status "Application available at: http://localhost:5000"
    print_status "Logs available at: logs/app.log"
}

# Start services (production)
start_production_services() {
    print_status "Starting production services with Docker..."
    
    cd "$PROJECT_ROOT"
    
    # Build Docker images
    print_status "Building Docker images..."
    docker-compose build
    
    # Start services
    print_status "Starting services..."
    docker-compose up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Health check
    if curl -f -s http://localhost:5000/api/system/health > /dev/null; then
        print_status "Production services started successfully ✅"
        print_status "Application available at: http://localhost:5000"
    else
        print_error "Health check failed. Check logs with: docker-compose logs"
        exit 1
    fi
}

# Setup monitoring (production only)
setup_monitoring() {
    if [ "$DEPLOYMENT_ENV" = "production" ]; then
        print_status "Setting up monitoring..."
        
        # Start Prometheus and Grafana
        docker-compose -f docker-compose.monitoring.yml up -d
        
        print_status "Monitoring setup completed ✅"
        print_status "Prometheus available at: http://localhost:9090"
        print_status "Grafana available at: http://localhost:3000"
    fi
}

# Generate sample data
generate_sample_data() {
    print_status "Generating sample data..."
    
    cd "$PROJECT_ROOT"
    source venv/bin/activate
    
    python -c "
import sys
sys.path.append('.')

from quantum.attribution_engine import QuantumAttributionEngine
from governance.quorum_system import QuorumGovernance, StakeholderType, ProposalType, VoteType
from metadata.dsi_manager import DSIMetadataManager

# Initialize components
quantum_engine = QuantumAttributionEngine()
governance = QuorumGovernance()
metadata_manager = DSIMetadataManager()

print('Registering sample stakeholders...')
# Register IPLC stakeholders
governance.register_stakeholder(
    'iplc_kayapo', 'Kayapó Representative', StakeholderType.IPLC_REPRESENTATIVE,
    community_affiliation='Kayapó Indigenous Territory'
)
governance.register_stakeholder(
    'iplc_maasai', 'Maasai Representative', StakeholderType.IPLC_REPRESENTATIVE,
    community_affiliation='Maasai Community'
)

# Register other stakeholders
governance.register_stakeholder(
    'researcher_001', 'Dr. Jane Smith', StakeholderType.RESEARCHER
)
governance.register_stakeholder(
    'pharma_corp', 'PharmaCorp Ltd', StakeholderType.INDUSTRY
)
governance.register_stakeholder(
    'cali_admin', 'Cali Fund Administrator', StakeholderType.CALI_FUND_ADMINISTRATOR
)

print('Creating sample DSI metadata...')
# Sample DSI data
sample_dsi = {
    'sequence_id': 'DEMO_001',
    'sequence_data': 'ATCGATCGATCG' * 100,
    'organism': 'Uncaria tomentosa',
    'collection_info': {
        'sequence_type': 'DNA',
        'collection_date': '2024-01-15',
        'collection_location': {'lat': -3.4653, 'lon': -62.2159},
        'tissue_type': 'leaf'
    },
    'fair_metadata': {
        'title': 'Demo Medicinal Plant Genome',
        'description': 'Sample genome sequence for system demonstration',
        'keywords': ['genomics', 'traditional knowledge', 'medicinal plants'],
        'creators': [
            {'name': 'Dr. Demo User', 'affiliation': 'Demo University'},
            {'name': 'Demo Indigenous Council', 'affiliation': 'Demo Territory'}
        ],
        'license': 'CC-BY-NC-SA',
        'usage_notes': 'Demo data for system testing',
        'citation': 'Demo et al. Sample genome. DSI Platform. 2024.'
    },
    'care_metadata': {
        'community_benefits': ['Research collaboration', 'Revenue sharing'],
        'benefit_sharing_terms': {'revenue_percentage': 0.02},
        'community_participation': True,
        'governance_structure': {
            'decision_body': 'Demo Traditional Council',
            'consent_mechanism': 'Community assembly'
        },
        'consent_requirements': {
            'community_name': 'Demo Indigenous Territory',
            'consent_given': True,
            'consent_date': '2024-01-10',
            'consent_scope': ['research', 'commercial'],
            'restrictions': ['weapons development'],
            'contact_person': 'Elder Demo Leader'
        },
        'ethical_review_status': 'Approved',
        'cultural_protocols': ['Respect boundaries'],
        'researcher_responsibilities': ['Progress reports'],
        'ethical_considerations': ['Knowledge protection'],
        'cultural_sensitivity': {'sacred_knowledge_excluded': True},
        'future_use_considerations': ['Conservation research']
    },
    'created_by': 'demo@dsi-platform.org'
}

metadata = metadata_manager.create_dsi_metadata(**sample_dsi)
print(f'Created sample DSI: {metadata.dsi_id}')

print('Sample data generation completed ✅')
"
    
    print_status "Sample data generated ✅"
}

# Display deployment summary
display_summary() {
    print_status "Deployment Summary"
    echo "================================================================"
    echo -e "Environment: ${YELLOW}${DEPLOYMENT_ENV}${NC}"
    echo -e "Application URL: ${YELLOW}http://localhost:5000${NC}"
    echo -e "API Documentation: ${YELLOW}http://localhost:5000/api${NC}"
    echo ""
    echo "Available API endpoints:"
    echo "  - GET  /api/system/health    - System health check"
    echo "  - GET  /api/system/stats     - System statistics"
    echo "  - POST /api/dsi/register     - Register DSI asset"
    echo "  - POST /api/quantum/attribute - Calculate attribution"
    echo "  - POST /api/governance/proposal - Submit proposal"
    echo ""
    if [ "$DEPLOYMENT_ENV" = "production" ]; then
        echo "Production services:"
        echo "  - Prometheus: http://localhost:9090"
        echo "  - Grafana: http://localhost:3000"
    fi
    echo ""
    echo "Log files:"
    echo "  - Application: logs/app.log"
    echo "  - System: logs/dsi_system.log"
    echo ""
    echo "To stop the application:"
    if [ "$DEPLOYMENT_ENV" = "production" ]; then
        echo "  docker-compose down"
    else
        echo "  kill \$(cat app.pid) && rm app.pid"
    fi
    echo "================================================================"
}

# Main deployment flow
main() {
    check_prerequisites
    setup_python_environment
    setup_configuration
    
    if [ "$DEPLOYMENT_ENV" = "production" ]; then
        setup_fabric_network
        initialize_databases
        run_tests
        start_production_services
        setup_monitoring
    else
        initialize_databases
        run_tests
        start_development_services
    fi
    
    generate_sample_data
    display_summary
    
    print_status "🎉 Deployment completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    "development"|"dev")
        DEPLOYMENT_ENV="development"
        main
        ;;
    "production"|"prod")
        DEPLOYMENT_ENV="production"
        main
        ;;
    "test")
        check_prerequisites
        setup_python_environment
        initialize_databases
        run_tests
        ;;
    "stop")
        if [ -f "app.pid" ]; then
            kill $(cat app.pid) && rm app.pid
            print_status "Development server stopped"
        else
            docker-compose down
            print_status "Production services stopped"
        fi
        ;;
    "clean")
        print_status "Cleaning up..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        rm -rf venv
        rm -f app.pid
        print_status "Cleanup completed"
        ;;
    *)
        echo "Usage: $0 {development|production|test|stop|clean}"
        echo ""
        echo "Commands:"
        echo "  development  - Deploy for development environment"
        echo "  production   - Deploy for production environment"
        echo "  test         - Run tests only"
        echo "  stop         - Stop running services"
        echo "  clean        - Clean up all containers and files"
        exit 1
        ;;
esac
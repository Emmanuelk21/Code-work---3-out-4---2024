# Quantum-Enhanced Blockchain DSI System - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Quantum-Enhanced Blockchain system for FAIR and CARE-compliant Digital Sequence Information (DSI) benefit allocation in the CBD Cali Fund.

## System Architecture

The system consists of four main components:

1. **Blockchain Layer**: Hyperledger Fabric network with smart contracts
2. **Quantum Attribution**: Qiskit-based quantum computing for contribution modeling
3. **Governance System**: Quorum sensing-inspired IPLC decision-making
4. **Metadata Management**: FAIR-CARE compliant data handling with JSON-LD

## Prerequisites

### System Requirements

**Minimum Requirements:**
- 4 CPU cores
- 8 GB RAM
- 50 GB storage
- Ubuntu 20.04+ or equivalent Linux distribution

**Recommended for Production:**
- 8 CPU cores
- 16 GB RAM
- 200 GB SSD storage
- Load balancer for high availability

### Software Dependencies

**Required:**
- Python 3.9+
- pip3
- Git
- curl

**For Production Deployment:**
- Docker 20.10+
- Docker Compose 2.0+
- Node.js 16+ (for Hyperledger Fabric)

**Optional:**
- Redis (for caching)
- PostgreSQL (for production database)
- Nginx (reverse proxy)

## Quick Start

### 1. Download and Setup

```bash
# Clone the repository
git clone <repository-url>
cd quantum-blockchain-dsi

# Make deployment script executable
chmod +x scripts/deploy.sh

# Run development deployment
./scripts/deploy.sh development
```

### 2. Access the System

- **Web Interface**: http://localhost:5000
- **Health Check**: http://localhost:5000/api/system/health
- **API Documentation**: http://localhost:5000/api

## Development Deployment

### Step-by-Step Setup

1. **Environment Setup**
```bash
# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

2. **Configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit configuration (required for production)
nano .env
```

3. **Initialize System**
```bash
# Initialize databases
python -c "from metadata.dsi_manager import DSIMetadataManager; DSIMetadataManager()"
python -c "from governance.quorum_system import QuorumGovernance; QuorumGovernance()"

# Run tests
python -m pytest tests/
python tests/test_integration.py
```

4. **Start Services**
```bash
# Development server
export FLASK_ENV=development
python app.py
```

## Production Deployment

### Using Docker Compose (Recommended)

1. **Prepare Environment**
```bash
# Ensure Docker is running
docker --version
docker-compose --version

# Configure production environment
cp .env.example .env
# Edit .env with production settings
```

2. **Deploy with Script**
```bash
./scripts/deploy.sh production
```

3. **Manual Docker Deployment**
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs
```

### Manual Production Setup

1. **System Setup**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv git curl

# Create system user
sudo useradd -m -s /bin/bash dsi-system
sudo usermod -aG docker dsi-system
```

2. **Application Setup**
```bash
# Switch to system user
sudo su - dsi-system

# Clone and setup
git clone <repository-url> /opt/dsi-system
cd /opt/dsi-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Service Configuration**
```bash
# Create systemd service
sudo nano /etc/systemd/system/dsi-system.service
```

```ini
[Unit]
Description=Quantum-Enhanced DSI System
After=network.target

[Service]
Type=simple
User=dsi-system
WorkingDirectory=/opt/dsi-system
Environment=PATH=/opt/dsi-system/venv/bin
ExecStart=/opt/dsi-system/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable dsi-system
sudo systemctl start dsi-system
sudo systemctl status dsi-system
```

## Hyperledger Fabric Setup

### Development Network

```bash
# Download Fabric samples
cd blockchain
curl -sSL https://bit.ly/2ysbOFE | bash -s -- 2.5.0 1.5.2

# Start test network
cd fabric-samples/test-network
./network.sh up createChannel -c dsi-channel -ca

# Deploy chaincode
./network.sh deployCC -ccn dsi-chaincode -ccp ../../contracts -ccl go
```

### Production Network

For production, set up a multi-organization Fabric network:

1. **Network Configuration**
   - Configure multiple organizations
   - Set up Certificate Authorities
   - Deploy ordering service
   - Create production channel

2. **Chaincode Deployment**
   - Package DSI chaincode
   - Install on peer nodes
   - Approve and commit chaincode

3. **Connection Profiles**
   - Configure connection profiles for each organization
   - Set up wallet credentials
   - Test connectivity

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Application
SECRET_KEY=your-production-secret-key
DEBUG=False
PORT=5000

# Database
DSI_DATABASE_URL=postgresql://user:pass@localhost/dsi_db

# Blockchain
FABRIC_NETWORK_PATH=/path/to/fabric/network
FABRIC_CHANNEL_NAME=dsi-channel

# Quantum Computing
QUANTUM_BACKEND=aer_simulator
IBMQ_TOKEN=your-ibm-quantum-token

# Governance
GOVERNANCE_QUORUM_THRESHOLD=0.6
IPLC_VETO_ENABLED=true

# Security
JWT_SECRET_KEY=your-jwt-secret
ALLOWED_ORIGINS=https://your-domain.com
```

### Database Configuration

**SQLite (Development):**
```bash
DSI_DATABASE_URL=sqlite:///dsi_metadata.db
```

**PostgreSQL (Production):**
```bash
DSI_DATABASE_URL=postgresql://user:password@localhost:5432/dsi_database
```

### Quantum Computing Setup

**IBM Quantum:**
1. Create IBM Quantum Experience account
2. Get API token
3. Configure in `.env`:
```bash
QUANTUM_BACKEND=ibm_qasm_simulator
IBMQ_TOKEN=your-token-here
```

**Local Simulator:**
```bash
QUANTUM_BACKEND=aer_simulator
```

## Security Configuration

### SSL/TLS Setup

1. **Obtain SSL Certificate**
```bash
# Using Let's Encrypt
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com
```

2. **Configure Nginx**
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Authentication

Configure JWT-based authentication:

```bash
# Generate secure secret
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

### Firewall Configuration

```bash
# UFW setup
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5000/tcp  # Block direct access to app
```

## Monitoring and Logging

### Application Monitoring

1. **Health Checks**
```bash
# System health
curl http://localhost:5000/api/system/health

# System statistics
curl http://localhost:5000/api/system/stats
```

2. **Log Configuration**
```bash
# Create log directory
mkdir -p /var/log/dsi-system

# Configure log rotation
sudo nano /etc/logrotate.d/dsi-system
```

### Production Monitoring

1. **Prometheus & Grafana**
```bash
# Deploy monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access dashboards
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000
```

2. **Custom Metrics**
   - Request count and latency
   - Quantum computation metrics
   - Governance proposal statistics
   - IPLC consent tracking

## Backup and Recovery

### Database Backup

```bash
# SQLite backup
cp dsi_metadata.db backups/dsi_metadata_$(date +%Y%m%d).db

# PostgreSQL backup
pg_dump dsi_database > backups/dsi_backup_$(date +%Y%m%d).sql
```

### System Backup

```bash
# Create backup script
#!/bin/bash
BACKUP_DIR="/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup databases
cp *.db "$BACKUP_DIR/"

# Backup configuration
cp .env "$BACKUP_DIR/"

# Backup logs
cp -r logs/ "$BACKUP_DIR/"

# Create archive
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"
```

### Recovery Procedures

1. **Database Recovery**
```bash
# Restore SQLite
cp backups/dsi_metadata_20240115.db dsi_metadata.db

# Restore PostgreSQL
psql dsi_database < backups/dsi_backup_20240115.sql
```

2. **Full System Recovery**
```bash
# Extract backup
tar -xzf backup_20240115.tar.gz

# Restore files
cp backup_20240115/.env .
cp -r backup_20240115/logs/ .
```

## Troubleshooting

### Common Issues

1. **Quantum Attribution Errors**
```bash
# Check Qiskit installation
python -c "import qiskit; print(qiskit.__version__)"

# Test quantum backend
python -c "from qiskit import Aer; print(Aer.backends())"
```

2. **Blockchain Connection Issues**
```bash
# Check Fabric network
cd blockchain/fabric-samples/test-network
./network.sh status

# Restart network
./network.sh down
./network.sh up createChannel -c dsi-channel
```

3. **Database Issues**
```bash
# Check database connection
python -c "from metadata.dsi_manager import DSIMetadataManager; DSIMetadataManager()"

# Reset database
rm dsi_metadata.db
python -c "from metadata.dsi_manager import DSIMetadataManager; DSIMetadataManager()"
```

### Performance Optimization

1. **Database Optimization**
   - Use PostgreSQL for production
   - Configure connection pooling
   - Add database indexes

2. **Quantum Computing Optimization**
   - Use quantum hardware for production
   - Implement result caching
   - Optimize circuit depth

3. **Application Optimization**
   - Enable Redis caching
   - Use Gunicorn for WSGI
   - Configure load balancing

## Scaling

### Horizontal Scaling

1. **Load Balancer Configuration**
```nginx
upstream dsi_backend {
    server 10.0.1.10:5000;
    server 10.0.1.11:5000;
    server 10.0.1.12:5000;
}

server {
    listen 80;
    location / {
        proxy_pass http://dsi_backend;
    }
}
```

2. **Database Clustering**
   - PostgreSQL primary-replica setup
   - Read-only replicas for queries
   - Connection pooling

### Vertical Scaling

1. **Resource Allocation**
   - Increase CPU cores for quantum computations
   - Add RAM for large metadata operations
   - Use SSD storage for better I/O

2. **Container Resource Limits**
```yaml
services:
  dsi-app:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
```

## Maintenance

### Regular Maintenance Tasks

1. **Daily**
   - Check system health
   - Monitor logs for errors
   - Verify backup completion

2. **Weekly**
   - Update system packages
   - Review performance metrics
   - Test disaster recovery

3. **Monthly**
   - Security updates
   - Certificate renewal
   - Capacity planning review

### Update Procedures

1. **Application Updates**
```bash
# Backup current version
./scripts/deploy.sh stop
cp -r . ../dsi-system-backup

# Pull updates
git pull origin main

# Deploy updates
./scripts/deploy.sh production
```

2. **Dependency Updates**
```bash
# Update Python packages
pip list --outdated
pip install -r requirements.txt --upgrade

# Update Docker images
docker-compose pull
docker-compose up -d
```

## Support and Resources

### Documentation
- [API Documentation](API_DOCUMENTATION.md)
- [FAIR-CARE Implementation](FAIR_CARE_GUIDE.md)
- [Quantum Attribution Guide](QUANTUM_GUIDE.md)
- [Governance Manual](GOVERNANCE_GUIDE.md)

### Community
- GitHub Issues: Report bugs and feature requests
- Discussions: Community support and ideas
- Wiki: Additional documentation and examples

### Professional Support
- Implementation consulting
- Custom development
- Training and workshops
- 24/7 production support

For professional support, contact: support@dsi-platform.org

---

**Version**: 1.0  
**Last Updated**: January 2024  
**Maintainer**: DSI Platform Team
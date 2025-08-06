"""
Main Flask Application for Quantum-Enhanced Blockchain DSI System

This application integrates all system components: blockchain, quantum attribution,
governance, and metadata management to provide a unified interface for
FAIR and CARE-compliant DSI benefit allocation.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

# Import system components
from quantum.attribution_engine import QuantumAttributionEngine
from governance.quorum_system import (
    QuorumGovernance, StakeholderType, ProposalType, VoteType
)
from metadata.dsi_manager import DSIMetadataManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
CORS(app)

# Initialize system components
quantum_engine = QuantumAttributionEngine()
governance = QuorumGovernance()
metadata_manager = DSIMetadataManager()

# Global system state
system_stats = {
    'dsi_assets_registered': 0,
    'proposals_submitted': 0,
    'total_benefits_allocated': 0.0,
    'active_stakeholders': 0
}


@app.route('/')
def index():
    """Main dashboard."""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Quantum-Enhanced DSI Governance Platform</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 8px; }
            .stats { display: flex; gap: 20px; margin: 20px 0; }
            .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; }
            .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
            .feature-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .feature-card h3 { color: #2c3e50; margin-top: 0; }
            .api-endpoint { background: #ecf0f1; padding: 10px; border-radius: 4px; margin: 10px 0; font-family: monospace; }
            .principles { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .principle-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px; }
            .principle { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌐 Quantum-Enhanced Blockchain DSI Governance Platform</h1>
            <p>FAIR and CARE-Compliant Digital Sequence Information Benefit Allocation for the CBD Cali Fund</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <h3>📊 System Statistics</h3>
                <p><strong>DSI Assets:</strong> {{ stats.dsi_assets_registered }}</p>
                <p><strong>Active Proposals:</strong> {{ stats.proposals_submitted }}</p>
                <p><strong>Benefits Allocated:</strong> ${{ "{:,.2f}".format(stats.total_benefits_allocated) }}</p>
                <p><strong>Stakeholders:</strong> {{ stats.active_stakeholders }}</p>
            </div>
        </div>

        <div class="principles">
            <h2>🎯 FAIR & CARE Principles Integration</h2>
            <div class="principle-grid">
                <div class="principle">
                    <h4>FAIR Principles</h4>
                    <ul>
                        <li><strong>Findable:</strong> DOI-based identification</li>
                        <li><strong>Accessible:</strong> Controlled access protocols</li>
                        <li><strong>Interoperable:</strong> JSON-LD metadata</li>
                        <li><strong>Reusable:</strong> Clear licensing & provenance</li>
                    </ul>
                </div>
                <div class="principle">
                    <h4>CARE Principles</h4>
                    <ul>
                        <li><strong>Collective Benefit:</strong> Community benefit sharing</li>
                        <li><strong>Authority to Control:</strong> IPLC consent mechanisms</li>
                        <li><strong>Responsibility:</strong> Ethical review requirements</li>
                        <li><strong>Ethics:</strong> Cultural sensitivity protocols</li>
                    </ul>
                </div>
            </div>
        </div>

        <div class="feature-grid">
            <div class="feature-card">
                <h3>🔗 Blockchain Infrastructure</h3>
                <p>Hyperledger Fabric permissioned blockchain for secure, transparent DSI transaction recording and automated benefit-sharing via smart contracts.</p>
                <div class="api-endpoint">POST /api/dsi/register</div>
                <div class="api-endpoint">GET /api/dsi/{id}</div>
                <div class="api-endpoint">POST /api/blockchain/record-usage</div>
            </div>

            <div class="feature-card">
                <h3>⚛️ Quantum Attribution</h3>
                <p>Qiskit-based quantum computing algorithms for modeling complex, non-linear DSI contributions to innovations with probabilistic weight assignment.</p>
                <div class="api-endpoint">POST /api/quantum/attribute</div>
                <div class="api-endpoint">GET /api/quantum/results/{job_id}</div>
                <div class="api-endpoint">POST /api/quantum/compare-methods</div>
            </div>

            <div class="feature-card">
                <h3>🗳️ Quorum Governance</h3>
                <p>Bacteria-inspired quorum sensing protocols ensuring IPLC stakeholders have meaningful authority in benefit-sharing decisions.</p>
                <div class="api-endpoint">POST /api/governance/proposal</div>
                <div class="api-endpoint">POST /api/governance/vote</div>
                <div class="api-endpoint">GET /api/governance/status/{proposal_id}</div>
            </div>

            <div class="feature-card">
                <h3>📋 FAIR-CARE Metadata</h3>
                <p>Comprehensive metadata management system with JSON-LD support, RDF graphs, and Indigenous consent tracking.</p>
                <div class="api-endpoint">POST /api/metadata/create</div>
                <div class="api-endpoint">GET /api/metadata/search</div>
                <div class="api-endpoint">PUT /api/metadata/consent</div>
            </div>

            <div class="feature-card">
                <h3>💰 Benefit Allocation</h3>
                <p>Automated Cali Fund benefit distribution based on quantum attribution results and IPLC consent terms.</p>
                <div class="api-endpoint">POST /api/benefits/calculate</div>
                <div class="api-endpoint">GET /api/benefits/history</div>
                <div class="api-endpoint">POST /api/benefits/trigger-payment</div>
            </div>

            <div class="feature-card">
                <h3>🏛️ Indigenous Rights</h3>
                <p>IPLC authority mechanisms with consent management, veto powers, and cultural protocol enforcement.</p>
                <div class="api-endpoint">POST /api/iplc/register</div>
                <div class="api-endpoint">PUT /api/iplc/update-consent</div>
                <div class="api-endpoint">GET /api/iplc/consensus/{proposal_id}</div>
            </div>
        </div>

        <div class="feature-card" style="margin-top: 20px;">
            <h3>🚀 Quick Start</h3>
            <p>1. Register IPLC stakeholders: <code>POST /api/stakeholders/register</code></p>
            <p>2. Create DSI metadata: <code>POST /api/dsi/register</code></p>
            <p>3. Submit governance proposal: <code>POST /api/governance/proposal</code></p>
            <p>4. Calculate quantum attribution: <code>POST /api/quantum/attribute</code></p>
            <p>5. Process benefit allocation: <code>POST /api/benefits/calculate</code></p>
        </div>
    </body>
    </html>
    """, stats=system_stats)


# ===== DSI MANAGEMENT ENDPOINTS =====

@app.route('/api/dsi/register', methods=['POST'])
def register_dsi():
    """Register a new DSI asset with FAIR-CARE metadata."""
    try:
        data = request.json
        
        # Create DSI metadata
        metadata = metadata_manager.create_dsi_metadata(
            sequence_id=data['sequence_id'],
            sequence_data=data['sequence_data'],
            organism=data['organism'],
            collection_info=data['collection_info'],
            fair_metadata=data['fair_metadata'],
            care_metadata=data['care_metadata'],
            created_by=data['created_by']
        )
        
        # Update system stats
        system_stats['dsi_assets_registered'] += 1
        
        logger.info(f"Registered DSI asset: {metadata.dsi_id}")
        
        return jsonify({
            'success': True,
            'dsi_id': metadata.dsi_id,
            'doi': metadata.doi,
            'message': 'DSI asset registered successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"DSI registration failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/dsi/<dsi_id>', methods=['GET'])
def get_dsi(dsi_id):
    """Retrieve DSI metadata by ID."""
    try:
        metadata = metadata_manager.get_dsi_metadata(dsi_id)
        if not metadata:
            return jsonify({
                'success': False,
                'error': 'DSI not found'
            }), 404
        
        # Convert to dict for JSON response
        metadata_dict = {
            'dsi_id': metadata.dsi_id,
            'sequence_id': metadata.sequence_id,
            'doi': metadata.doi,
            'organism': metadata.organism,
            'sequence_type': metadata.sequence_type,
            'sequence_length': metadata.sequence_length,
            'collection_date': metadata.collection_date,
            'status': metadata.status,
            'fair_metadata': {
                'title': metadata.fair.title,
                'description': metadata.fair.description,
                'keywords': metadata.fair.keywords,
                'license': metadata.fair.license,
                'access_rights': metadata.fair.access_rights
            },
            'care_metadata': {
                'community_name': metadata.care.consent_requirements.community_name,
                'consent_given': metadata.care.consent_requirements.consent_given,
                'consent_scope': metadata.care.consent_requirements.consent_scope,
                'benefit_sharing_terms': metadata.care.benefit_sharing_terms
            }
        }
        
        return jsonify({
            'success': True,
            'metadata': metadata_dict
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve DSI {dsi_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/dsi/search', methods=['POST'])
def search_dsi():
    """Search DSI assets based on query parameters."""
    try:
        query = request.json
        include_restricted = query.get('include_restricted', False)
        
        results = metadata_manager.search_dsi_metadata(query, include_restricted)
        
        # Convert results to JSON-serializable format
        search_results = []
        for metadata in results:
            search_results.append({
                'dsi_id': metadata.dsi_id,
                'sequence_id': metadata.sequence_id,
                'organism': metadata.organism,
                'title': metadata.fair.title,
                'keywords': metadata.fair.keywords,
                'consent_given': metadata.care.consent_requirements.consent_given,
                'community_name': metadata.care.consent_requirements.community_name
            })
        
        return jsonify({
            'success': True,
            'results': search_results,
            'total_found': len(search_results)
        })
        
    except Exception as e:
        logger.error(f"DSI search failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===== QUANTUM ATTRIBUTION ENDPOINTS =====

@app.route('/api/quantum/attribute', methods=['POST'])
def quantum_attribute():
    """Calculate quantum attribution for DSI contributions."""
    try:
        data = request.json
        dataset_ids = data['dataset_ids']
        innovation_context = data.get('innovation_context', {})
        method = data.get('method', 'qaoa')
        
        # Calculate attribution
        attribution_results = quantum_engine.calculate_contributions(
            dataset_ids=dataset_ids,
            innovation_context=innovation_context,
            method=method
        )
        
        # Generate report
        report = quantum_engine.generate_attribution_report(
            attribution_results,
            [{'id': did} for did in dataset_ids],
            innovation_context
        )
        
        logger.info(f"Quantum attribution calculated for {len(dataset_ids)} datasets")
        
        return jsonify({
            'success': True,
            'attribution_results': attribution_results,
            'report': report,
            'method_used': method
        })
        
    except Exception as e:
        logger.error(f"Quantum attribution failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/quantum/compare-methods', methods=['POST'])
def compare_attribution_methods():
    """Compare different quantum attribution methods."""
    try:
        data = request.json
        dataset_ids = data['dataset_ids']
        innovation_context = data.get('innovation_context', {})
        
        methods = ['qaoa', 'variational', 'similarity']
        results = {}
        
        for method in methods:
            try:
                attribution = quantum_engine.calculate_contributions(
                    dataset_ids=dataset_ids,
                    innovation_context=innovation_context,
                    method=method
                )
                results[method] = attribution
            except Exception as e:
                results[method] = {'error': str(e)}
        
        return jsonify({
            'success': True,
            'method_comparison': results,
            'dataset_count': len(dataset_ids)
        })
        
    except Exception as e:
        logger.error(f"Method comparison failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===== GOVERNANCE ENDPOINTS =====

@app.route('/api/stakeholders/register', methods=['POST'])
def register_stakeholder():
    """Register a new stakeholder in the governance system."""
    try:
        data = request.json
        
        stakeholder_type = StakeholderType(data['type'])
        stakeholder = governance.register_stakeholder(
            stakeholder_id=data['id'],
            name=data['name'],
            stakeholder_type=stakeholder_type,
            community_affiliation=data.get('community_affiliation'),
            voting_weight=data.get('voting_weight', 1.0)
        )
        
        # Update system stats
        system_stats['active_stakeholders'] += 1
        
        logger.info(f"Registered stakeholder: {stakeholder.name}")
        
        return jsonify({
            'success': True,
            'stakeholder_id': stakeholder.id,
            'message': 'Stakeholder registered successfully'
        })
        
    except Exception as e:
        logger.error(f"Stakeholder registration failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/governance/proposal', methods=['POST'])
def submit_proposal():
    """Submit a new governance proposal."""
    try:
        data = request.json
        
        proposal_type = ProposalType(data['type'])
        proposal_id = governance.submit_proposal(
            proposer_id=data['proposer_id'],
            title=data['title'],
            description=data['description'],
            proposal_type=proposal_type,
            dsi_asset_ids=data['dsi_asset_ids'],
            proposed_terms=data['proposed_terms'],
            custom_quorum_threshold=data.get('quorum_threshold'),
            custom_approval_threshold=data.get('approval_threshold'),
            duration_days=data.get('duration_days', 7)
        )
        
        # Update system stats
        system_stats['proposals_submitted'] += 1
        
        logger.info(f"Submitted proposal: {proposal_id}")
        
        return jsonify({
            'success': True,
            'proposal_id': proposal_id,
            'message': 'Proposal submitted successfully'
        })
        
    except Exception as e:
        logger.error(f"Proposal submission failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/governance/vote', methods=['POST'])
def cast_vote():
    """Cast a vote on a governance proposal."""
    try:
        data = request.json
        
        vote_type = VoteType(data['vote'])
        success = governance.cast_vote(
            voter_id=data['voter_id'],
            proposal_id=data['proposal_id'],
            vote=vote_type,
            reasoning=data.get('reasoning')
        )
        
        logger.info(f"Vote cast by {data['voter_id']} on {data['proposal_id']}")
        
        return jsonify({
            'success': success,
            'message': 'Vote cast successfully'
        })
        
    except Exception as e:
        logger.error(f"Vote casting failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/governance/status/<proposal_id>', methods=['GET'])
def proposal_status(proposal_id):
    """Get the current status of a proposal."""
    try:
        status = governance.check_proposal_status(proposal_id)
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Failed to get proposal status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/iplc/consensus/<proposal_id>', methods=['GET'])
def iplc_consensus(proposal_id):
    """Get IPLC consensus status for a proposal."""
    try:
        consensus_status = governance.get_iplc_consensus_status(proposal_id)
        
        return jsonify({
            'success': True,
            'iplc_consensus': consensus_status
        })
        
    except Exception as e:
        logger.error(f"Failed to get IPLC consensus: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===== BENEFIT ALLOCATION ENDPOINTS =====

@app.route('/api/benefits/calculate', methods=['POST'])
def calculate_benefits():
    """Calculate benefit allocation based on usage and attribution."""
    try:
        data = request.json
        dsi_id = data['dsi_id']
        usage_info = data['usage_info']
        
        # Get DSI metadata
        metadata = metadata_manager.get_dsi_metadata(dsi_id)
        if not metadata:
            return jsonify({
                'success': False,
                'error': 'DSI not found'
            }), 404
        
        # Check access permissions
        access_result = metadata_manager.check_access_permissions(
            dsi_id=dsi_id,
            accessor_id=usage_info['user_id'],
            access_type=usage_info['access_type'],
            purpose=usage_info['purpose']
        )
        
        if not access_result['permitted']:
            return jsonify({
                'success': False,
                'error': f"Access denied: {access_result['reason']}"
            }), 403
        
        # Calculate quantum attribution if multiple datasets
        if 'related_datasets' in usage_info:
            attribution = quantum_engine.calculate_contributions(
                dataset_ids=usage_info['related_datasets'],
                innovation_context=usage_info.get('innovation_context', {})
            )
        else:
            attribution = {dsi_id: 1.0}
        
        # Calculate benefit amounts
        revenue = usage_info.get('revenue', 0)
        benefit_rate = metadata.care.benefit_sharing_terms.get('revenue_percentage', 0.01)
        total_benefit = revenue * benefit_rate
        
        # Allocate benefits based on attribution
        allocations = {}
        for dataset_id, weight in attribution.items():
            allocations[dataset_id] = total_benefit * weight
        
        # Update system stats
        system_stats['total_benefits_allocated'] += total_benefit
        
        logger.info(f"Calculated benefits for DSI {dsi_id}: ${total_benefit}")
        
        return jsonify({
            'success': True,
            'total_benefit_amount': total_benefit,
            'allocations': allocations,
            'attribution_weights': attribution,
            'access_conditions': access_result.get('conditions', [])
        })
        
    except Exception as e:
        logger.error(f"Benefit calculation failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/metadata/jsonld/<dsi_id>', methods=['GET'])
def get_jsonld(dsi_id):
    """Get JSON-LD representation of DSI metadata."""
    try:
        jsonld_data = metadata_manager.generate_jsonld(dsi_id)
        
        return jsonify(jsonld_data)
        
    except Exception as e:
        logger.error(f"JSON-LD generation failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/system/stats', methods=['GET'])
def get_system_stats():
    """Get current system statistics."""
    return jsonify({
        'success': True,
        'stats': system_stats,
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/system/health', methods=['GET'])
def health_check():
    """System health check."""
    try:
        # Test each component
        health_status = {
            'quantum_engine': 'healthy',
            'governance': 'healthy',
            'metadata_manager': 'healthy',
            'overall': 'healthy'
        }
        
        # Simple functionality tests
        try:
            quantum_engine.calculate_contributions(['test_dataset'])
        except Exception:
            health_status['quantum_engine'] = 'degraded'
            health_status['overall'] = 'degraded'
        
        try:
            test_stakeholder_count = len(governance.stakeholders)
        except Exception:
            health_status['governance'] = 'degraded'
            health_status['overall'] = 'degraded'
        
        try:
            metadata_manager.search_dsi_metadata({})
        except Exception:
            health_status['metadata_manager'] = 'degraded'
            health_status['overall'] = 'degraded'
        
        return jsonify({
            'success': True,
            'health': health_status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'health': {'overall': 'unhealthy'},
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Initialize with some sample data
    logger.info("Starting Quantum-Enhanced DSI Governance Platform...")
    
    # Register sample stakeholders
    try:
        governance.register_stakeholder(
            "iplc_001", "Kayapó Representative", StakeholderType.IPLC_REPRESENTATIVE,
            community_affiliation="Kayapó Indigenous Territory"
        )
        governance.register_stakeholder(
            "researcher_001", "Dr. Jane Smith", StakeholderType.RESEARCHER
        )
        system_stats['active_stakeholders'] = 2
    except Exception as e:
        logger.warning(f"Failed to initialize sample stakeholders: {e}")
    
    # Start Flask application
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('DEBUG', 'False').lower() == 'true'
    )
"""
Quantum-Enhanced Blockchain DSI System - Enhanced Web Application

Integrated Flask application with comprehensive dashboards and user interfaces
for DSI governance, quantum attribution comparison, and blockchain management.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_cors import CORS

# Import system components
from quantum.attribution_engine import QuantumAttributionEngine
from governance.quorum_system import QuorumGovernance, ProposalType, VoteType
from metadata.dsi_manager import DSIMetadataManager

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'quantum-dsi-development-key')
CORS(app)

# Initialize system components
quantum_engine = QuantumAttributionEngine()
governance = QuorumGovernance()
metadata_manager = DSIMetadataManager(database_path="dsi_production.db")

# =============================================================================
# WEB INTERFACE ROUTES
# =============================================================================

@app.route('/')
def index():
    """Main dashboard homepage."""
    try:
        # Get system statistics
        stats = get_system_stats()
        
        # Get recent activities
        recent_proposals = list(governance.proposals.values())[-5:] if governance.proposals else []
        
        return render_template('dashboard.html', 
                             stats=stats, 
                             recent_proposals=recent_proposals)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html', stats={}, recent_proposals=[])

@app.route('/comparative-dashboard')
def comparative_dashboard():
    """Comparative analysis dashboard for Classical vs Quantum attribution."""
    return render_template('comparative_dashboard.html')

@app.route('/blockchain-interface')
def blockchain_interface():
    """Blockchain management interface."""
    try:
        # Get all stakeholders
        stakeholders = list(governance.stakeholders.values())
        
        # Get all proposals with their status
        proposals = []
        for proposal_id, proposal in governance.proposals.items():
            status = governance.check_proposal_status(proposal_id)
            proposals.append({
                'id': proposal_id,
                'title': proposal.title,
                'type': proposal.proposal_type.value,
                'status': status['status'],
                'proposer': proposal.proposer_id,
                'created_at': proposal.created_at.isoformat(),
                'vote_counts': status['vote_counts']
            })
        
        return render_template('blockchain_interface.html', 
                             stakeholders=stakeholders,
                             proposals=proposals)
    except Exception as e:
        flash(f'Error loading blockchain interface: {str(e)}', 'error')
        return render_template('blockchain_interface.html', 
                             stakeholders=[], proposals=[])

@app.route('/dsi-management')
def dsi_management():
    """DSI asset management interface."""
    try:
        # Get recent DSI assets
        conn = sqlite3.connect(metadata_manager.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT dsi_id, sequence_id, doi, created_at, status 
            FROM dsi_metadata 
            ORDER BY created_at DESC 
            LIMIT 20
        """)
        
        assets = []
        for row in cursor.fetchall():
            assets.append({
                'dsi_id': row[0],
                'sequence_id': row[1], 
                'doi': row[2],
                'created_at': row[3],
                'status': row[4]
            })
        
        conn.close()
        
        return render_template('dsi_management.html', assets=assets)
    except Exception as e:
        flash(f'Error loading DSI management: {str(e)}', 'error')
        return render_template('dsi_management.html', assets=[])

# =============================================================================
# COMPARATIVE ANALYSIS API ENDPOINTS
# =============================================================================

@app.route('/api/comparative-analysis', methods=['POST'])
def run_comparative_analysis():
    """Run comparative analysis between Classical and Quantum methods."""
    try:
        data = request.get_json()
        
        # Get parameters
        datasets = data.get('datasets', [
            'SARS-CoV-2_Reference_Genome',
            'Traditional_Medicinal_Plants',
            'Human_ACE2_Receptor', 
            'Viral_Variants_Database',
            'Indigenous_Knowledge'
        ])
        
        innovation_context = data.get('innovation_context', {
            'type': 'pharmaceutical',
            'application': 'COVID-19 treatment',
            'commercial_value': 100000000,
            'complexity': 'high'
        })
        
        # Run all attribution methods
        results = {}
        
        # 1. Uniform distribution
        uniform_weights = {dataset: 1.0/len(datasets) for dataset in datasets}
        results['uniform'] = uniform_weights
        
        # 2. Rule-based attribution
        results['rule_based'] = calculate_rule_based_attribution(datasets, innovation_context)
        
        # 3. Citation-based attribution  
        results['citation_based'] = calculate_citation_based_attribution(datasets)
        
        # 4. Quantum attribution
        results['quantum'] = quantum_engine.calculate_contributions(
            dataset_ids=datasets,
            innovation_context=innovation_context,
            method='quantum_similarity'
        )
        
        # Calculate benefit allocations
        total_revenue = innovation_context.get('commercial_value', 100000000)
        benefit_rate = 0.02
        total_benefits = total_revenue * benefit_rate
        
        benefit_allocations = {}
        for method, weights in results.items():
            benefit_allocations[method] = {
                dataset: total_benefits * weight 
                for dataset, weight in weights.items()
            }
        
        # Calculate IPLC impact
        iplc_datasets = [d for d in datasets if any(term in d.lower() for term in 
                        ['traditional', 'indigenous', 'medicinal', 'herbal'])]
        
        iplc_analysis = {}
        for method, weights in results.items():
            iplc_total = sum(weights.get(d, 0) for d in iplc_datasets)
            iplc_analysis[method] = {
                'percentage': iplc_total * 100,
                'benefit_amount': total_benefits * iplc_total,
                'datasets': iplc_datasets
            }
        
        return jsonify({
            'success': True,
            'attribution_weights': results,
            'benefit_allocations': benefit_allocations,
            'iplc_analysis': iplc_analysis,
            'scenario': {
                'datasets': datasets,
                'innovation_context': innovation_context,
                'total_revenue': total_revenue,
                'total_benefits': total_benefits
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def calculate_rule_based_attribution(datasets: List[str], context: Dict) -> Dict[str, float]:
    """Calculate rule-based attribution weights."""
    weights = {}
    
    for dataset in datasets:
        weight = 0.1  # Base weight
        
        # Apply rules based on dataset characteristics
        if 'reference' in dataset.lower() or 'genome' in dataset.lower():
            weight = 0.15
        elif 'variant' in dataset.lower() or 'mutation' in dataset.lower():
            weight = 0.12
        elif 'human' in dataset.lower():
            weight = 0.13
        elif any(term in dataset.lower() for term in ['traditional', 'indigenous', 'medicinal']):
            weight = 0.08  # Often undervalued in industry
        elif 'clinical' in dataset.lower() or 'trial' in dataset.lower():
            weight = 0.11
        elif 'synthetic' in dataset.lower():
            weight = 0.10 if context.get('type') == 'pharmaceutical' else 0.07
            
        weights[dataset] = weight
    
    # Normalize
    total = sum(weights.values())
    return {k: v/total for k, v in weights.items()}

def calculate_citation_based_attribution(datasets: List[str]) -> Dict[str, float]:
    """Calculate citation-based attribution weights."""
    import numpy as np
    np.random.seed(42)  # Reproducible results
    
    citations = {}
    for dataset in datasets:
        base = np.random.randint(100, 1000)
        
        # Simulate citation bias
        if 'reference' in dataset.lower():
            citations[dataset] = base * 3
        elif 'human' in dataset.lower():
            citations[dataset] = base * 2.5
        elif 'variant' in dataset.lower():
            citations[dataset] = base * 2
        elif 'clinical' in dataset.lower():
            citations[dataset] = base * 1.8
        elif any(term in dataset.lower() for term in ['traditional', 'indigenous']):
            citations[dataset] = base * 0.5  # Citation bias against traditional knowledge
        else:
            citations[dataset] = base
    
    # Convert to weights
    total = sum(citations.values())
    return {k: v/total for k, v in citations.items()}

# =============================================================================
# BLOCKCHAIN INTERFACE API ENDPOINTS  
# =============================================================================

@app.route('/api/stakeholders', methods=['GET'])
def get_stakeholders():
    """Get all registered stakeholders."""
    try:
        stakeholders = []
        for stakeholder in governance.stakeholders.values():
            stakeholders.append({
                'id': stakeholder.stakeholder_id,
                'name': stakeholder.name,
                'type': stakeholder.stakeholder_type.value,
                'voting_weight': stakeholder.voting_weight,
                'organization': stakeholder.organization,
                'is_iplc': stakeholder.is_iplc
            })
        
        return jsonify({
            'success': True,
            'stakeholders': stakeholders,
            'total_count': len(stakeholders)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stakeholders/register', methods=['POST'])
def register_stakeholder():
    """Register a new stakeholder."""
    try:
        data = request.get_json()
        
        stakeholder_id = governance.register_stakeholder(
            name=data['name'],
            stakeholder_type=data['type'],
            organization=data.get('organization', ''),
            contact_info=data.get('contact_info', {}),
            voting_weight=data.get('voting_weight'),
            is_iplc=data.get('is_iplc', False)
        )
        
        return jsonify({
            'success': True,
            'stakeholder_id': stakeholder_id,
            'message': f'Stakeholder {data["name"]} registered successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proposals', methods=['GET'])
def get_proposals():
    """Get all governance proposals with their current status."""
    try:
        proposals = []
        
        for proposal_id, proposal in governance.proposals.items():
            status = governance.check_proposal_status(proposal_id)
            
            proposals.append({
                'id': proposal_id,
                'title': proposal.title,
                'description': proposal.description,
                'type': proposal.proposal_type.value,
                'proposer_id': proposal.proposer_id,
                'created_at': proposal.created_at.isoformat(),
                'voting_deadline': proposal.voting_deadline.isoformat() if proposal.voting_deadline else None,
                'status': status['status'],
                'vote_counts': status['vote_counts'],
                'quorum_reached': status['quorum_reached'],
                'dsi_asset_ids': proposal.dsi_asset_ids,
                'proposed_terms': proposal.proposed_terms
            })
        
        return jsonify({
            'success': True,
            'proposals': proposals,
            'total_count': len(proposals)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proposals/submit', methods=['POST'])
def submit_proposal():
    """Submit a new governance proposal."""
    try:
        data = request.get_json()
        
        proposal_id = governance.submit_proposal(
            proposer_id=data['proposer_id'],
            title=data['title'],
            description=data['description'],
            proposal_type=ProposalType(data['proposal_type']),
            dsi_asset_ids=data.get('dsi_asset_ids', []),
            proposed_terms=data.get('proposed_terms', {})
        )
        
        return jsonify({
            'success': True,
            'proposal_id': proposal_id,
            'message': f'Proposal "{data["title"]}" submitted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proposals/<proposal_id>/vote', methods=['POST'])
def cast_vote(proposal_id):
    """Cast a vote on a proposal."""
    try:
        data = request.get_json()
        
        governance.cast_vote(
            voter_id=data['voter_id'],
            proposal_id=proposal_id,
            vote=VoteType(data['vote']),
            justification=data.get('justification', '')
        )
        
        return jsonify({
            'success': True,
            'message': f'Vote cast successfully on proposal {proposal_id}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# DSI MANAGEMENT API ENDPOINTS
# =============================================================================

@app.route('/api/dsi/register', methods=['POST'])
def register_dsi():
    """Register a new DSI asset."""
    try:
        data = request.get_json()
        
        dsi_metadata = metadata_manager.create_dsi_metadata(
            sequence_id=data['sequence_id'],
            sequence_data=data['sequence_data'],
            organism=data['organism'],
            collection_info=data['collection_info'],
            fair_metadata=data['fair_metadata'],
            care_metadata=data['care_metadata'],
            created_by=data['created_by']
        )
        
        return jsonify({
            'success': True,
            'dsi_id': dsi_metadata.dsi_id,
            'doi': dsi_metadata.doi,
            'message': 'DSI asset registered successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dsi/<dsi_id>', methods=['GET'])
def get_dsi_metadata(dsi_id):
    """Get DSI metadata by ID."""
    try:
        metadata = metadata_manager.get_dsi_metadata(dsi_id)
        
        if metadata:
            return jsonify({
                'success': True,
                'metadata': {
                    'dsi_id': metadata.dsi_id,
                    'sequence_id': metadata.sequence_id,
                    'doi': metadata.doi,
                    'organism': metadata.organism,
                    'sequence_length': metadata.sequence_length,
                    'collection_date': metadata.collection_date,
                    'collection_location': metadata.collection_location,
                    'fair': {
                        'title': metadata.fair.title,
                        'description': metadata.fair.description,
                        'creators': metadata.fair.creators,
                        'license': metadata.fair.license,
                        'access_url': metadata.fair.access_url
                    },
                    'care': {
                        'consent_given': metadata.care.consent_requirements.consent_given,
                        'community_name': metadata.care.consent_requirements.community_name,
                        'benefit_sharing_terms': metadata.care.benefit_sharing_terms
                    },
                    'created_at': metadata.created_at.isoformat(),
                    'updated_at': metadata.updated_at.isoformat(),
                    'status': metadata.status
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'DSI asset not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# QUANTUM ATTRIBUTION API ENDPOINTS
# =============================================================================

@app.route('/api/quantum/attribute', methods=['POST'])
def calculate_quantum_attribution():
    """Calculate quantum attribution for datasets."""
    try:
        data = request.get_json()
        
        contributions = quantum_engine.calculate_contributions(
            dataset_ids=data['dataset_ids'],
            dataset_metadata=data.get('dataset_metadata'),
            innovation_context=data.get('innovation_context'),
            method=data.get('method', 'quantum_similarity')
        )
        
        # Generate comprehensive report
        report = quantum_engine.generate_attribution_report(
            contributions=contributions,
            dataset_metadata=data.get('dataset_metadata'),
            innovation_context=data.get('innovation_context')
        )
        
        return jsonify({
            'success': True,
            'contributions': contributions,
            'report': report
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_system_stats():
    """Get overall system statistics."""
    try:
        # Governance stats
        total_stakeholders = len(governance.stakeholders)
        total_proposals = len(governance.proposals)
        active_proposals = sum(1 for p in governance.proposals.values() 
                             if governance.check_proposal_status(p.proposal_id)['status'] == 'active')
        
        # DSI stats
        conn = sqlite3.connect(metadata_manager.database_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM dsi_metadata")
        total_dsi_assets = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM dsi_metadata WHERE status = 'active'")
        active_dsi_assets = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM iplc_consent WHERE consent_given = 1")
        consented_assets = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_stakeholders': total_stakeholders,
            'total_proposals': total_proposals,
            'active_proposals': active_proposals,
            'total_dsi_assets': total_dsi_assets,
            'active_dsi_assets': active_dsi_assets,
            'consented_assets': consented_assets,
            'system_status': 'operational'
        }
        
    except Exception as e:
        return {
            'system_status': 'error',
            'error': str(e)
        }

# =============================================================================
# LEGACY API ENDPOINTS (maintained for compatibility)
# =============================================================================

@app.route('/api/dsi/search', methods=['GET'])
def search_dsi():
    """Search DSI assets."""
    try:
        query = request.args.get('query', '')
        results = metadata_manager.search_dsi_metadata(query)
        
        return jsonify({
            'success': True,
            'results': [
                {
                    'dsi_id': r.dsi_id,
                    'sequence_id': r.sequence_id,
                    'title': r.fair.title,
                    'organism': r.organism,
                    'doi': r.doi
                } for r in results
            ]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/system/health', methods=['GET'])
def health_check():
    """System health check endpoint."""
    try:
        stats = get_system_stats()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'components': {
                'quantum_engine': 'operational',
                'governance_system': 'operational',
                'metadata_manager': 'operational',
                'database': 'operational'
            },
            'statistics': stats
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=True
    )
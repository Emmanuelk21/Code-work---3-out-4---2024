"""
Comprehensive Integration Tests for Quantum-Enhanced DSI System

This test suite validates the entire system workflow from DSI registration
through quantum attribution to benefit allocation, ensuring FAIR and CARE
compliance throughout.
"""

import pytest
import json
import time
from typing import Dict, List

# Import system components
from quantum.attribution_engine import QuantumAttributionEngine
from governance.quorum_system import (
    QuorumGovernance, StakeholderType, ProposalType, VoteType
)
from metadata.dsi_manager import DSIMetadataManager


class TestDSISystemIntegration:
    """Integration tests for the complete DSI governance system."""
    
    @pytest.fixture
    def quantum_engine(self):
        """Initialize quantum attribution engine."""
        return QuantumAttributionEngine()
    
    @pytest.fixture
    def governance(self):
        """Initialize governance system."""
        return QuorumGovernance()
    
    @pytest.fixture
    def metadata_manager(self):
        """Initialize metadata manager."""
        return DSIMetadataManager(database_path=":memory:")  # In-memory for testing
    
    @pytest.fixture
    def sample_stakeholders(self, governance):
        """Register sample stakeholders for testing."""
        stakeholders = {}
        
        # IPLC representatives
        stakeholders['iplc_kayapo'] = governance.register_stakeholder(
            "iplc_kayapo", "Kayapó Representative", StakeholderType.IPLC_REPRESENTATIVE,
            community_affiliation="Kayapó Indigenous Territory"
        )
        
        stakeholders['iplc_maasai'] = governance.register_stakeholder(
            "iplc_maasai", "Maasai Representative", StakeholderType.IPLC_REPRESENTATIVE,
            community_affiliation="Maasai Community"
        )
        
        # Researchers
        stakeholders['researcher'] = governance.register_stakeholder(
            "researcher_001", "Dr. Jane Smith", StakeholderType.RESEARCHER
        )
        
        # Industry
        stakeholders['industry'] = governance.register_stakeholder(
            "pharma_corp", "PharmaCorp", StakeholderType.INDUSTRY
        )
        
        # Cali Fund administrator
        stakeholders['admin'] = governance.register_stakeholder(
            "cali_admin", "Cali Fund Administrator", StakeholderType.CALI_FUND_ADMINISTRATOR
        )
        
        return stakeholders
    
    @pytest.fixture
    def sample_dsi_metadata(self):
        """Generate sample DSI metadata for testing."""
        return {
            'sequence_id': 'KY_COVID_001',
            'sequence_data': 'ATCGATCGATCG' * 200,  # Mock sequence
            'organism': 'Uncaria tomentosa',
            'collection_info': {
                'sequence_type': 'DNA',
                'collection_date': '2024-01-15',
                'collection_location': {'lat': -3.4653, 'lon': -62.2159},
                'tissue_type': 'leaf'
            },
            'fair_metadata': {
                'title': 'Medicinal Plant Genome from Kayapó Territory',
                'description': 'Complete genome sequence for traditional medicine research',
                'keywords': ['genomics', 'traditional knowledge', 'medicinal plants'],
                'creators': [
                    {'name': 'Dr. Maria Santos', 'affiliation': 'University of São Paulo'},
                    {'name': 'Kayapó Traditional Council', 'affiliation': 'Kayapó Territory'}
                ],
                'license': 'CC-BY-NC-SA',
                'usage_notes': 'Restricted to non-commercial research with benefit sharing',
                'citation': 'Santos et al. Medicinal plant genome. DSI Platform. 2024.'
            },
            'care_metadata': {
                'community_benefits': [
                    'Research collaboration',
                    'Revenue sharing',
                    'Traditional knowledge documentation'
                ],
                'benefit_sharing_terms': {
                    'revenue_percentage': 0.02,
                    'minimum_payment': 10000
                },
                'community_participation': True,
                'governance_structure': {
                    'decision_body': 'Kayapó Traditional Council',
                    'consent_mechanism': 'Community assembly'
                },
                'consent_requirements': {
                    'community_name': 'Kayapó Indigenous Territory',
                    'consent_given': True,
                    'consent_date': '2024-01-10',
                    'consent_expires': '2029-01-10',
                    'consent_scope': ['research', 'commercial'],
                    'restrictions': ['weapons development', 'sacred knowledge'],
                    'contact_person': 'Elder João Kayapó'
                },
                'ethical_review_status': 'Approved by Indigenous Ethics Committee',
                'cultural_protocols': ['Respect for sacred boundaries'],
                'researcher_responsibilities': ['Annual progress reports'],
                'ethical_considerations': ['Traditional knowledge protection'],
                'cultural_sensitivity': {'sacred_knowledge_excluded': True},
                'future_use_considerations': ['Climate change research']
            },
            'created_by': 'dr.maria.santos@usp.br'
        }

    def test_complete_dsi_workflow(self, quantum_engine, governance, metadata_manager, 
                                 sample_stakeholders, sample_dsi_metadata):
        """Test the complete DSI governance workflow."""
        
        # Step 1: Register DSI asset with FAIR-CARE metadata
        dsi_metadata = metadata_manager.create_dsi_metadata(**sample_dsi_metadata)
        
        assert dsi_metadata is not None
        assert dsi_metadata.dsi_id is not None
        assert dsi_metadata.doi.startswith('10.5061/dsi.')
        assert dsi_metadata.care.consent_requirements.consent_given is True
        
        # Step 2: Submit governance proposal for benefit sharing
        proposal_id = governance.submit_proposal(
            proposer_id="pharma_corp",
            title="COVID-19 Vaccine Development Benefit Sharing",
            description="Proposal to share 2% of vaccine revenues with Kayapó community",
            proposal_type=ProposalType.BENEFIT_SHARING_APPROVAL,
            dsi_asset_ids=[dsi_metadata.dsi_id],
            proposed_terms={
                'revenue_share_percentage': 0.02,
                'estimated_revenue': 50000000,
                'payment_frequency': 'quarterly'
            }
        )
        
        assert proposal_id is not None
        
        # Step 3: Stakeholders vote on proposal
        # IPLC representatives approve
        governance.cast_vote("iplc_kayapo", proposal_id, VoteType.APPROVE, 
                           "Fair terms for our community")
        governance.cast_vote("iplc_maasai", proposal_id, VoteType.APPROVE, 
                           "Supports Indigenous rights")
        
        # Researcher approves
        governance.cast_vote("researcher_001", proposal_id, VoteType.APPROVE,
                           "Ethical benefit sharing")
        
        # Industry approves
        governance.cast_vote("pharma_corp", proposal_id, VoteType.APPROVE,
                           "Committed to fair practices")
        
        # Administrator approves
        governance.cast_vote("cali_admin", proposal_id, VoteType.APPROVE,
                           "Aligns with Cali Fund objectives")
        
        # Step 4: Check proposal status and IPLC consensus
        status = governance.check_proposal_status(proposal_id)
        assert status['quorum_reached'] is True
        
        iplc_consensus = governance.get_iplc_consensus_status(proposal_id)
        assert iplc_consensus['iplc_consensus_reached'] is True
        assert iplc_consensus['iplc_approval_rate'] == 1.0
        
        # Step 5: Finalize proposal
        decision = governance.finalize_proposal(proposal_id)
        assert decision.decision == "approved"
        
        # Step 6: Calculate quantum attribution for multi-dataset scenario
        dataset_ids = [
            dsi_metadata.dsi_id,
            "reference_genome_001",
            "variant_database_002"
        ]
        
        innovation_context = {
            'type': 'pharmaceutical',
            'complexity': 0.8,
            'commercial_value': 50000000,
            'application': 'COVID-19 vaccine development'
        }
        
        attribution_results = quantum_engine.calculate_contributions(
            dataset_ids=dataset_ids,
            innovation_context=innovation_context,
            method='qaoa'
        )
        
        # Verify attribution results
        assert len(attribution_results) == len(dataset_ids)
        assert abs(sum(attribution_results.values()) - 1.0) < 0.01  # Should sum to ~1.0
        assert dsi_metadata.dsi_id in attribution_results
        
        # Step 7: Test access permission checking
        access_result = metadata_manager.check_access_permissions(
            dsi_id=dsi_metadata.dsi_id,
            accessor_id="pharma_corp",
            access_type="commercial_use",
            purpose="developing COVID-19 vaccine"
        )
        
        assert access_result['permitted'] is True
        assert 'sacred knowledge' not in access_result.get('conditions', [])
        
        # Step 8: Calculate benefit allocation
        revenue = 50000000
        benefit_rate = dsi_metadata.care.benefit_sharing_terms['revenue_percentage']
        total_benefit = revenue * benefit_rate
        
        # Allocate based on quantum attribution
        allocations = {}
        for dataset_id, weight in attribution_results.items():
            allocations[dataset_id] = total_benefit * weight
        
        # Verify benefit calculations
        assert total_benefit == 1000000  # 2% of 50M
        assert abs(sum(allocations.values()) - total_benefit) < 0.01
        assert allocations[dsi_metadata.dsi_id] > 0
        
        print(f"\n✅ Complete DSI workflow test passed!")
        print(f"   DSI ID: {dsi_metadata.dsi_id}")
        print(f"   Proposal approved: {decision.decision}")
        print(f"   IPLC consensus: {iplc_consensus['iplc_consensus_reached']}")
        print(f"   Total benefit: ${total_benefit:,.2f}")
        print(f"   Attribution to Kayapó DSI: {attribution_results[dsi_metadata.dsi_id]:.2%}")

    def test_iplc_veto_power(self, governance, sample_stakeholders):
        """Test IPLC veto power in governance decisions."""
        
        # Submit a potentially harmful proposal
        proposal_id = governance.submit_proposal(
            proposer_id="pharma_corp",
            title="Unrestricted Commercial Access",
            description="Proposal for unrestricted commercial use without benefit sharing",
            proposal_type=ProposalType.DATA_ACCESS_REQUEST,
            dsi_asset_ids=["test_dsi_001"],
            proposed_terms={
                'access_type': 'unrestricted',
                'revenue_share_percentage': 0.0,
                'restrictions': 'none'
            }
        )
        
        # IPLCs reject the proposal
        governance.cast_vote("iplc_kayapo", proposal_id, VoteType.REJECT,
                           "Does not protect our rights")
        governance.cast_vote("iplc_maasai", proposal_id, VoteType.REJECT,
                           "Unacceptable terms")
        
        # Others might approve
        governance.cast_vote("researcher_001", proposal_id, VoteType.APPROVE,
                           "Would facilitate research")
        governance.cast_vote("pharma_corp", proposal_id, VoteType.APPROVE,
                           "Benefits our development")
        
        # Check IPLC consensus and veto
        iplc_status = governance.get_iplc_consensus_status(proposal_id)
        assert iplc_status['iplc_veto_triggered'] is True
        
        # Finalize and verify veto effect
        decision = governance.finalize_proposal(proposal_id)
        assert decision.decision == "rejected_iplc_veto"
        
        print(f"\n✅ IPLC veto power test passed!")
        print(f"   Proposal rejected due to IPLC veto")
        print(f"   IPLC rejection rate: {(1 - iplc_status['iplc_approval_rate']):.0%}")

    def test_fair_care_compliance(self, metadata_manager, sample_dsi_metadata):
        """Test FAIR and CARE principles compliance."""
        
        # Create DSI with FAIR-CARE metadata
        dsi_metadata = metadata_manager.create_dsi_metadata(**sample_dsi_metadata)
        
        # Test FAIR compliance
        # Findable: Has persistent identifier (DOI)
        assert dsi_metadata.doi is not None
        assert dsi_metadata.doi.startswith('10.5061/')
        
        # Accessible: Has access terms and restrictions
        assert dsi_metadata.fair.access_rights is not None
        assert dsi_metadata.fair.license is not None
        
        # Interoperable: Can generate JSON-LD
        jsonld_data = metadata_manager.generate_jsonld(dsi_metadata.dsi_id)
        assert jsonld_data['@type'] == 'schema:Dataset'
        assert 'care:consentGiven' in jsonld_data
        
        # Reusable: Has clear provenance and usage terms
        assert dsi_metadata.fair.usage_notes is not None
        assert dsi_metadata.fair.citation is not None
        
        # Test CARE compliance
        # Collective Benefit: Has benefit sharing terms
        assert len(dsi_metadata.care.community_benefits) > 0
        assert 'revenue_percentage' in dsi_metadata.care.benefit_sharing_terms
        
        # Authority to Control: Has IPLC consent mechanisms
        assert dsi_metadata.care.consent_requirements.consent_given is not None
        assert dsi_metadata.care.consent_requirements.community_name is not None
        
        # Responsibility: Has ethical review and cultural protocols
        assert dsi_metadata.care.ethical_review_status is not None
        assert len(dsi_metadata.care.cultural_protocols) > 0
        
        # Ethics: Has ethical considerations and cultural sensitivity
        assert len(dsi_metadata.care.ethical_considerations) > 0
        assert dsi_metadata.care.cultural_sensitivity is not None
        
        print(f"\n✅ FAIR-CARE compliance test passed!")
        print(f"   DOI: {dsi_metadata.doi}")
        print(f"   IPLC consent: {dsi_metadata.care.consent_requirements.consent_given}")
        print(f"   Benefit sharing: {dsi_metadata.care.benefit_sharing_terms['revenue_percentage']:.1%}")

    def test_quantum_attribution_methods(self, quantum_engine):
        """Test different quantum attribution methods."""
        
        dataset_ids = ['dataset_001', 'dataset_002', 'dataset_003', 'dataset_004']
        innovation_context = {
            'type': 'pharmaceutical',
            'complexity': 0.6,
            'commercial_value': 10000000
        }
        
        methods = ['qaoa', 'variational', 'similarity']
        results = {}
        
        for method in methods:
            attribution = quantum_engine.calculate_contributions(
                dataset_ids=dataset_ids,
                innovation_context=innovation_context,
                method=method
            )
            
            # Verify basic properties
            assert len(attribution) == len(dataset_ids)
            assert all(weight >= 0 for weight in attribution.values())
            assert abs(sum(attribution.values()) - 1.0) < 0.1  # Should approximately sum to 1
            
            results[method] = attribution
        
        # Compare method results
        for method, attribution in results.items():
            print(f"\n{method.upper()} Attribution:")
            for dataset_id, weight in attribution.items():
                print(f"   {dataset_id}: {weight:.3f}")
        
        print(f"\n✅ Quantum attribution methods test passed!")
        print(f"   Tested {len(methods)} methods on {len(dataset_ids)} datasets")

    def test_consent_management(self, metadata_manager, sample_dsi_metadata):
        """Test IPLC consent management and updates."""
        
        # Create DSI with initial consent
        dsi_metadata = metadata_manager.create_dsi_metadata(**sample_dsi_metadata)
        initial_consent = dsi_metadata.care.consent_requirements.consent_given
        
        # Test consent update by authorized IPLC representative
        consent_updates = {
            'consent_given': False,
            'restrictions': ['all commercial use suspended']
        }
        
        # This should succeed (simulated IPLC authority)
        success = metadata_manager.update_iplc_consent(
            dsi_id=dsi_metadata.dsi_id,
            consent_updates=consent_updates,
            updated_by="kayapo.elder@indigenous.org"
        )
        
        assert success is True
        
        # Verify consent was updated
        updated_metadata = metadata_manager.get_dsi_metadata(dsi_metadata.dsi_id)
        assert updated_metadata.care.consent_requirements.consent_given is False
        assert 'all commercial use suspended' in updated_metadata.care.consent_requirements.restrictions
        
        # Test access permission with updated consent
        access_result = metadata_manager.check_access_permissions(
            dsi_id=dsi_metadata.dsi_id,
            accessor_id="commercial_user",
            access_type="commercial_use",
            purpose="product development"
        )
        
        assert access_result['permitted'] is False
        assert 'consent not given' in access_result['reason'].lower()
        
        print(f"\n✅ Consent management test passed!")
        print(f"   Initial consent: {initial_consent}")
        print(f"   Updated consent: {updated_metadata.care.consent_requirements.consent_given}")
        print(f"   Commercial access denied: {not access_result['permitted']}")

    def test_metadata_search_and_discovery(self, metadata_manager, sample_dsi_metadata):
        """Test metadata search and discovery functionality."""
        
        # Create multiple DSI assets
        dsi_assets = []
        
        # Kayapó medicinal plant
        kayapo_metadata = metadata_manager.create_dsi_metadata(**sample_dsi_metadata)
        dsi_assets.append(kayapo_metadata)
        
        # Maasai traditional medicine
        maasai_data = sample_dsi_metadata.copy()
        maasai_data['sequence_id'] = 'MS_TM_001'
        maasai_data['organism'] = 'Aloe vera'
        maasai_data['fair_metadata']['title'] = 'Aloe Vera Genome from Maasai Territory'
        maasai_data['care_metadata']['consent_requirements']['community_name'] = 'Maasai Community'
        
        maasai_metadata = metadata_manager.create_dsi_metadata(**maasai_data)
        dsi_assets.append(maasai_metadata)
        
        # Test search by organism
        search_results = metadata_manager.search_dsi_metadata({
            'organism': 'Uncaria'
        })
        
        assert len(search_results) == 1
        assert search_results[0].organism == 'Uncaria tomentosa'
        
        # Test search by keywords
        search_results = metadata_manager.search_dsi_metadata({
            'keywords': ['medicinal']
        })
        
        assert len(search_results) >= 1
        
        # Test JSON-LD generation for interoperability
        for dsi_asset in dsi_assets:
            jsonld_data = metadata_manager.generate_jsonld(dsi_asset.dsi_id)
            
            # Verify JSON-LD structure
            assert '@context' in jsonld_data
            assert '@type' in jsonld_data
            assert 'schema:identifier' in jsonld_data
            assert 'care:consentGiven' in jsonld_data
        
        print(f"\n✅ Metadata search and discovery test passed!")
        print(f"   Created {len(dsi_assets)} DSI assets")
        print(f"   Search by organism found {len(search_results)} results")

    def test_benefit_allocation_scenarios(self, quantum_engine, metadata_manager, sample_dsi_metadata):
        """Test various benefit allocation scenarios."""
        
        # Create test DSI
        dsi_metadata = metadata_manager.create_dsi_metadata(**sample_dsi_metadata)
        
        # Scenario 1: Single dataset usage
        single_dataset_attribution = quantum_engine.calculate_contributions([dsi_metadata.dsi_id])
        assert abs(single_dataset_attribution[dsi_metadata.dsi_id] - 1.0) < 0.01
        
        # Scenario 2: Multi-dataset collaboration
        dataset_ids = [dsi_metadata.dsi_id, 'reference_001', 'database_002']
        multi_attribution = quantum_engine.calculate_contributions(dataset_ids)
        
        # Calculate benefits for different revenue levels
        revenues = [1000000, 10000000, 100000000]  # $1M, $10M, $100M
        benefit_rate = 0.02  # 2%
        
        for revenue in revenues:
            total_benefit = revenue * benefit_rate
            
            # Allocate based on attribution
            allocations = {}
            for dataset_id, weight in multi_attribution.items():
                allocations[dataset_id] = total_benefit * weight
            
            # Verify allocations
            assert abs(sum(allocations.values()) - total_benefit) < 0.01
            assert allocations[dsi_metadata.dsi_id] > 0
            
            print(f"   Revenue ${revenue:,} → Benefit ${total_benefit:,} → Kayapó share ${allocations[dsi_metadata.dsi_id]:,.0f}")
        
        print(f"\n✅ Benefit allocation scenarios test passed!")

    def test_system_resilience(self, quantum_engine, governance, metadata_manager):
        """Test system resilience and error handling."""
        
        # Test invalid DSI ID
        invalid_metadata = metadata_manager.get_dsi_metadata("invalid_id")
        assert invalid_metadata is None
        
        # Test invalid proposal ID
        with pytest.raises(ValueError):
            governance.check_proposal_status("invalid_proposal")
        
        # Test quantum attribution with empty dataset list
        empty_attribution = quantum_engine.calculate_contributions([])
        assert len(empty_attribution) == 0
        
        # Test access permission for non-existent DSI
        access_result = metadata_manager.check_access_permissions(
            "non_existent", "user_id", "research", "study purpose"
        )
        assert access_result['permitted'] is False
        assert 'not found' in access_result['reason'].lower()
        
        print(f"\n✅ System resilience test passed!")
        print(f"   Handled invalid inputs gracefully")


def run_integration_tests():
    """Run all integration tests."""
    test_instance = TestDSISystemIntegration()
    
    # Initialize fixtures
    quantum_engine = QuantumAttributionEngine()
    governance = QuorumGovernance()
    metadata_manager = DSIMetadataManager(database_path=":memory:")
    
    # Register stakeholders
    stakeholders = {}
    stakeholders['iplc_kayapo'] = governance.register_stakeholder(
        "iplc_kayapo", "Kayapó Representative", StakeholderType.IPLC_REPRESENTATIVE,
        community_affiliation="Kayapó Indigenous Territory"
    )
    stakeholders['iplc_maasai'] = governance.register_stakeholder(
        "iplc_maasai", "Maasai Representative", StakeholderType.IPLC_REPRESENTATIVE,
        community_affiliation="Maasai Community"
    )
    stakeholders['researcher'] = governance.register_stakeholder(
        "researcher_001", "Dr. Jane Smith", StakeholderType.RESEARCHER
    )
    stakeholders['industry'] = governance.register_stakeholder(
        "pharma_corp", "PharmaCorp", StakeholderType.INDUSTRY
    )
    stakeholders['admin'] = governance.register_stakeholder(
        "cali_admin", "Cali Fund Administrator", StakeholderType.CALI_FUND_ADMINISTRATOR
    )
    
    # Sample DSI metadata
    sample_dsi_metadata = {
        'sequence_id': 'KY_COVID_001',
        'sequence_data': 'ATCGATCGATCG' * 200,
        'organism': 'Uncaria tomentosa',
        'collection_info': {
            'sequence_type': 'DNA',
            'collection_date': '2024-01-15',
            'collection_location': {'lat': -3.4653, 'lon': -62.2159},
            'tissue_type': 'leaf'
        },
        'fair_metadata': {
            'title': 'Medicinal Plant Genome from Kayapó Territory',
            'description': 'Complete genome sequence for traditional medicine research',
            'keywords': ['genomics', 'traditional knowledge', 'medicinal plants'],
            'creators': [
                {'name': 'Dr. Maria Santos', 'affiliation': 'University of São Paulo'},
                {'name': 'Kayapó Traditional Council', 'affiliation': 'Kayapó Territory'}
            ],
            'license': 'CC-BY-NC-SA',
            'usage_notes': 'Restricted to non-commercial research with benefit sharing',
            'citation': 'Santos et al. Medicinal plant genome. DSI Platform. 2024.'
        },
        'care_metadata': {
            'community_benefits': [
                'Research collaboration',
                'Revenue sharing',
                'Traditional knowledge documentation'
            ],
            'benefit_sharing_terms': {
                'revenue_percentage': 0.02,
                'minimum_payment': 10000
            },
            'community_participation': True,
            'governance_structure': {
                'decision_body': 'Kayapó Traditional Council',
                'consent_mechanism': 'Community assembly'
            },
            'consent_requirements': {
                'community_name': 'Kayapó Indigenous Territory',
                'consent_given': True,
                'consent_date': '2024-01-10',
                'consent_expires': '2029-01-10',
                'consent_scope': ['research', 'commercial'],
                'restrictions': ['weapons development', 'sacred knowledge'],
                'contact_person': 'Elder João Kayapó'
            },
            'ethical_review_status': 'Approved by Indigenous Ethics Committee',
            'cultural_protocols': ['Respect for sacred boundaries'],
            'researcher_responsibilities': ['Annual progress reports'],
            'ethical_considerations': ['Traditional knowledge protection'],
            'cultural_sensitivity': {'sacred_knowledge_excluded': True},
            'future_use_considerations': ['Climate change research']
        },
        'created_by': 'dr.maria.santos@usp.br'
    }
    
    print("🧪 Running DSI System Integration Tests...")
    print("=" * 60)
    
    # Run tests
    try:
        test_instance.test_complete_dsi_workflow(
            quantum_engine, governance, metadata_manager, stakeholders, sample_dsi_metadata
        )
        
        test_instance.test_iplc_veto_power(governance, stakeholders)
        
        test_instance.test_fair_care_compliance(metadata_manager, sample_dsi_metadata)
        
        test_instance.test_quantum_attribution_methods(quantum_engine)
        
        test_instance.test_consent_management(metadata_manager, sample_dsi_metadata)
        
        test_instance.test_metadata_search_and_discovery(metadata_manager, sample_dsi_metadata)
        
        test_instance.test_benefit_allocation_scenarios(quantum_engine, metadata_manager, sample_dsi_metadata)
        
        test_instance.test_system_resilience(quantum_engine, governance, metadata_manager)
        
        print("\n" + "=" * 60)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Quantum-Enhanced DSI System is fully operational")
        print("✅ FAIR and CARE principles are properly implemented")
        print("✅ Indigenous rights and governance are protected")
        print("✅ Benefit allocation mechanisms are functional")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    run_integration_tests()
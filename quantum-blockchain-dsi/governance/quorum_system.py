"""
Quorum Sensing-Inspired Governance System for DSI Governance

This module implements a decentralized governance system inspired by bacterial
quorum sensing, ensuring Indigenous Peoples and Local Communities (IPLCs) have
authority and control in DSI benefit-sharing decisions.
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StakeholderType(Enum):
    """Types of stakeholders in the governance system."""
    IPLC_REPRESENTATIVE = "iplc_representative"
    RESEARCHER = "researcher"
    INDUSTRY = "industry"
    CALI_FUND_ADMINISTRATOR = "cali_fund_administrator"
    GOVERNMENT = "government"
    NGO = "ngo"


class ProposalType(Enum):
    """Types of governance proposals."""
    BENEFIT_SHARING_APPROVAL = "benefit_sharing_approval"
    DATA_ACCESS_REQUEST = "data_access_request"
    CONSENT_MODIFICATION = "consent_modification"
    FUND_ALLOCATION = "fund_allocation"
    POLICY_CHANGE = "policy_change"
    DISPUTE_RESOLUTION = "dispute_resolution"


class VoteType(Enum):
    """Types of votes."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class Stakeholder:
    """Represents a stakeholder in the governance system."""
    id: str
    name: str
    type: StakeholderType
    public_key: str
    community_affiliation: Optional[str] = None
    voting_weight: float = 1.0
    reputation_score: float = 1.0
    is_active: bool = True
    joined_at: str = ""
    last_activity: str = ""


@dataclass
class QuorumVote:
    """Represents a vote in the quorum system."""
    voter_id: str
    proposal_id: str
    vote: VoteType
    timestamp: str
    signature: str
    reasoning: Optional[str] = None
    delegation_chain: Optional[List[str]] = None


@dataclass
class GovernanceProposal:
    """Represents a governance proposal."""
    id: str
    title: str
    description: str
    type: ProposalType
    proposer_id: str
    dsi_asset_ids: List[str]
    proposed_terms: Dict
    quorum_threshold: float
    approval_threshold: float
    created_at: str
    expires_at: str
    status: str = "active"
    votes: List[QuorumVote] = None
    decision_rationale: Optional[str] = None
    
    def __post_init__(self):
        if self.votes is None:
            self.votes = []


@dataclass
class QuorumDecision:
    """Represents the outcome of quorum decision-making."""
    proposal_id: str
    decision: str  # "approved", "rejected", "insufficient_quorum"
    total_eligible_voters: int
    total_votes_cast: int
    approval_votes: int
    rejection_votes: int
    abstain_votes: int
    quorum_reached: bool
    approval_threshold_met: bool
    decision_timestamp: str
    participating_stakeholders: List[str]


class QuorumGovernance:
    """
    Quorum sensing-inspired governance system for DSI decision-making.
    
    Implements decentralized decision-making protocols that ensure IPLC
    stakeholders have meaningful authority in governance decisions.
    """
    
    def __init__(self, 
                 default_quorum_threshold: float = 0.6,
                 default_approval_threshold: float = 0.5,
                 iplc_veto_enabled: bool = True):
        """
        Initialize the quorum governance system.
        
        Args:
            default_quorum_threshold: Minimum participation rate for valid decisions
            default_approval_threshold: Minimum approval rate for passage
            iplc_veto_enabled: Whether IPLCs have veto power over certain decisions
        """
        self.stakeholders: Dict[str, Stakeholder] = {}
        self.proposals: Dict[str, GovernanceProposal] = {}
        self.decisions: Dict[str, QuorumDecision] = {}
        self.default_quorum_threshold = default_quorum_threshold
        self.default_approval_threshold = default_approval_threshold
        self.iplc_veto_enabled = iplc_veto_enabled
        
        # Quorum sensing parameters inspired by bacterial systems
        self.signal_threshold = 0.3  # Minimum signal strength to trigger response
        self.signal_decay_rate = 0.1  # Rate at which signals decay over time
        self.cooperation_bonus = 0.1  # Bonus for cooperative voting patterns
        
        logger.info("Initialized QuorumGovernance system")
    
    def register_stakeholder(self,
                           stakeholder_id: str,
                           name: str,
                           stakeholder_type: StakeholderType,
                           community_affiliation: Optional[str] = None,
                           voting_weight: float = 1.0) -> Stakeholder:
        """
        Register a new stakeholder in the governance system.
        
        Args:
            stakeholder_id: Unique identifier for the stakeholder
            name: Display name
            stakeholder_type: Type of stakeholder
            community_affiliation: IPLC community if applicable
            voting_weight: Voting weight (IPLCs may have higher weights)
            
        Returns:
            Registered Stakeholder object
        """
        # Generate cryptographic keys for secure voting
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        # Serialize public key
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # IPLC representatives get higher voting weights
        if stakeholder_type == StakeholderType.IPLC_REPRESENTATIVE:
            voting_weight = max(voting_weight, 1.5)
        
        stakeholder = Stakeholder(
            id=stakeholder_id,
            name=name,
            type=stakeholder_type,
            public_key=public_key_pem.decode(),
            community_affiliation=community_affiliation,
            voting_weight=voting_weight,
            reputation_score=1.0,
            is_active=True,
            joined_at=self._current_timestamp(),
            last_activity=self._current_timestamp()
        )
        
        self.stakeholders[stakeholder_id] = stakeholder
        
        logger.info(f"Registered stakeholder: {name} ({stakeholder_type.value})")
        return stakeholder
    
    def submit_proposal(self,
                       proposer_id: str,
                       title: str,
                       description: str,
                       proposal_type: ProposalType,
                       dsi_asset_ids: List[str],
                       proposed_terms: Dict,
                       custom_quorum_threshold: Optional[float] = None,
                       custom_approval_threshold: Optional[float] = None,
                       duration_days: int = 7) -> str:
        """
        Submit a new governance proposal.
        
        Args:
            proposer_id: ID of the proposing stakeholder
            title: Proposal title
            description: Detailed description
            proposal_type: Type of proposal
            dsi_asset_ids: DSI assets affected by this proposal
            proposed_terms: Specific terms being proposed
            custom_quorum_threshold: Custom quorum threshold if needed
            custom_approval_threshold: Custom approval threshold if needed
            duration_days: Duration in days before proposal expires
            
        Returns:
            Proposal ID
        """
        # Validate proposer
        if proposer_id not in self.stakeholders:
            raise ValueError(f"Unknown proposer: {proposer_id}")
        
        if not self.stakeholders[proposer_id].is_active:
            raise ValueError(f"Proposer {proposer_id} is not active")
        
        # Generate proposal ID
        proposal_id = self._generate_proposal_id(proposer_id, title)
        
        # Set thresholds
        quorum_threshold = custom_quorum_threshold or self.default_quorum_threshold
        approval_threshold = custom_approval_threshold or self.default_approval_threshold
        
        # IPLC-related proposals may require higher thresholds
        if (proposal_type in [ProposalType.BENEFIT_SHARING_APPROVAL, 
                             ProposalType.CONSENT_MODIFICATION] or
            any(self._is_iplc_related_asset(asset_id) for asset_id in dsi_asset_ids)):
            quorum_threshold = max(quorum_threshold, 0.7)
            approval_threshold = max(approval_threshold, 0.6)
        
        # Calculate expiration time
        expires_at = self._add_days_to_timestamp(self._current_timestamp(), duration_days)
        
        proposal = GovernanceProposal(
            id=proposal_id,
            title=title,
            description=description,
            type=proposal_type,
            proposer_id=proposer_id,
            dsi_asset_ids=dsi_asset_ids,
            proposed_terms=proposed_terms,
            quorum_threshold=quorum_threshold,
            approval_threshold=approval_threshold,
            created_at=self._current_timestamp(),
            expires_at=expires_at,
            status="active",
            votes=[]
        )
        
        self.proposals[proposal_id] = proposal
        
        # Update proposer activity
        self.stakeholders[proposer_id].last_activity = self._current_timestamp()
        
        # Trigger quorum sensing signal
        self._emit_quorum_signal(proposal_id, "proposal_submitted")
        
        logger.info(f"Submitted proposal: {title} (ID: {proposal_id})")
        return proposal_id
    
    def cast_vote(self,
                  voter_id: str,
                  proposal_id: str,
                  vote: VoteType,
                  reasoning: Optional[str] = None,
                  delegate_to: Optional[str] = None) -> bool:
        """
        Cast a vote on a governance proposal.
        
        Args:
            voter_id: ID of the voting stakeholder
            proposal_id: ID of the proposal to vote on
            vote: Vote type (approve/reject/abstain)
            reasoning: Optional reasoning for the vote
            delegate_to: Optional delegation to another stakeholder
            
        Returns:
            True if vote was successfully cast
        """
        # Validate voter
        if voter_id not in self.stakeholders:
            raise ValueError(f"Unknown voter: {voter_id}")
        
        voter = self.stakeholders[voter_id]
        if not voter.is_active:
            raise ValueError(f"Voter {voter_id} is not active")
        
        # Validate proposal
        if proposal_id not in self.proposals:
            raise ValueError(f"Unknown proposal: {proposal_id}")
        
        proposal = self.proposals[proposal_id]
        if proposal.status != "active":
            raise ValueError(f"Proposal {proposal_id} is not active")
        
        # Check if proposal has expired
        if self._current_timestamp() > proposal.expires_at:
            proposal.status = "expired"
            raise ValueError(f"Proposal {proposal_id} has expired")
        
        # Check if voter has already voted
        existing_vote = next((v for v in proposal.votes if v.voter_id == voter_id), None)
        if existing_vote:
            raise ValueError(f"Voter {voter_id} has already voted on proposal {proposal_id}")
        
        # Handle delegation
        delegation_chain = []
        if delegate_to:
            delegation_chain = self._resolve_delegation_chain(voter_id, delegate_to)
        
        # Create vote signature
        vote_data = {
            'voter_id': voter_id,
            'proposal_id': proposal_id,
            'vote': vote.value,
            'timestamp': self._current_timestamp()
        }
        signature = self._sign_vote(vote_data, voter_id)
        
        # Create vote record
        quorum_vote = QuorumVote(
            voter_id=voter_id,
            proposal_id=proposal_id,
            vote=vote,
            timestamp=vote_data['timestamp'],
            signature=signature,
            reasoning=reasoning,
            delegation_chain=delegation_chain
        )
        
        proposal.votes.append(quorum_vote)
        
        # Update voter activity
        voter.last_activity = self._current_timestamp()
        
        # Update reputation based on voting patterns
        self._update_reputation(voter_id, proposal_id, vote)
        
        # Emit quorum sensing signal
        self._emit_quorum_signal(proposal_id, f"vote_cast_{vote.value}")
        
        # Check if quorum sensing triggers early decision
        if self._should_trigger_early_decision(proposal_id):
            self._finalize_proposal(proposal_id)
        
        logger.info(f"Vote cast by {voter_id} on proposal {proposal_id}: {vote.value}")
        return True
    
    def check_proposal_status(self, proposal_id: str) -> Dict:
        """
        Check the current status of a proposal.
        
        Args:
            proposal_id: ID of the proposal to check
            
        Returns:
            Dictionary with current proposal status and vote counts
        """
        if proposal_id not in self.proposals:
            raise ValueError(f"Unknown proposal: {proposal_id}")
        
        proposal = self.proposals[proposal_id]
        
        # Count votes
        vote_counts = self._count_votes(proposal_id)
        
        # Check if expired
        if self._current_timestamp() > proposal.expires_at and proposal.status == "active":
            proposal.status = "expired"
            if vote_counts['total_votes'] >= self._get_quorum_requirement(proposal_id):
                self._finalize_proposal(proposal_id)
        
        # Get eligible voters
        eligible_voters = self._get_eligible_voters(proposal_id)
        
        status = {
            'proposal_id': proposal_id,
            'title': proposal.title,
            'status': proposal.status,
            'created_at': proposal.created_at,
            'expires_at': proposal.expires_at,
            'vote_counts': vote_counts,
            'eligible_voters': len(eligible_voters),
            'quorum_threshold': proposal.quorum_threshold,
            'approval_threshold': proposal.approval_threshold,
            'quorum_requirement': self._get_quorum_requirement(proposal_id),
            'quorum_reached': vote_counts['total_votes'] >= self._get_quorum_requirement(proposal_id),
            'time_remaining': self._calculate_time_remaining(proposal.expires_at),
            'iplc_consensus': self._check_iplc_consensus(proposal_id)
        }
        
        return status
    
    def finalize_proposal(self, proposal_id: str) -> QuorumDecision:
        """
        Manually finalize a proposal (usually called when expired).
        
        Args:
            proposal_id: ID of the proposal to finalize
            
        Returns:
            QuorumDecision object with the final decision
        """
        return self._finalize_proposal(proposal_id)
    
    def get_stakeholder_voting_history(self, stakeholder_id: str) -> List[Dict]:
        """
        Get voting history for a stakeholder.
        
        Args:
            stakeholder_id: ID of the stakeholder
            
        Returns:
            List of voting records
        """
        if stakeholder_id not in self.stakeholders:
            raise ValueError(f"Unknown stakeholder: {stakeholder_id}")
        
        voting_history = []
        for proposal_id, proposal in self.proposals.items():
            vote = next((v for v in proposal.votes if v.voter_id == stakeholder_id), None)
            if vote:
                voting_history.append({
                    'proposal_id': proposal_id,
                    'proposal_title': proposal.title,
                    'vote': vote.vote.value,
                    'timestamp': vote.timestamp,
                    'reasoning': vote.reasoning
                })
        
        return sorted(voting_history, key=lambda x: x['timestamp'], reverse=True)
    
    def get_iplc_consensus_status(self, proposal_id: str) -> Dict:
        """
        Get detailed IPLC consensus status for a proposal.
        
        Args:
            proposal_id: ID of the proposal
            
        Returns:
            Dictionary with IPLC consensus details
        """
        if proposal_id not in self.proposals:
            raise ValueError(f"Unknown proposal: {proposal_id}")
        
        proposal = self.proposals[proposal_id]
        
        # Get IPLC stakeholders
        iplc_stakeholders = [s for s in self.stakeholders.values() 
                           if s.type == StakeholderType.IPLC_REPRESENTATIVE and s.is_active]
        
        # Get IPLC votes
        iplc_votes = []
        for vote in proposal.votes:
            if (vote.voter_id in self.stakeholders and 
                self.stakeholders[vote.voter_id].type == StakeholderType.IPLC_REPRESENTATIVE):
                iplc_votes.append(vote)
        
        # Calculate IPLC consensus metrics
        total_iplc = len(iplc_stakeholders)
        iplc_voted = len(iplc_votes)
        iplc_approve = len([v for v in iplc_votes if v.vote == VoteType.APPROVE])
        iplc_reject = len([v for v in iplc_votes if v.vote == VoteType.REJECT])
        iplc_abstain = len([v for v in iplc_votes if v.vote == VoteType.ABSTAIN])
        
        iplc_participation_rate = iplc_voted / total_iplc if total_iplc > 0 else 0
        iplc_approval_rate = iplc_approve / iplc_voted if iplc_voted > 0 else 0
        
        # Check for IPLC veto conditions
        iplc_veto_threshold = 0.3  # 30% of IPLCs can veto
        iplc_veto_triggered = (iplc_reject / total_iplc) >= iplc_veto_threshold if total_iplc > 0 else False
        
        return {
            'total_iplc_stakeholders': total_iplc,
            'iplc_votes_cast': iplc_voted,
            'iplc_approve': iplc_approve,
            'iplc_reject': iplc_reject,
            'iplc_abstain': iplc_abstain,
            'iplc_participation_rate': iplc_participation_rate,
            'iplc_approval_rate': iplc_approval_rate,
            'iplc_veto_enabled': self.iplc_veto_enabled,
            'iplc_veto_triggered': iplc_veto_triggered,
            'iplc_consensus_reached': iplc_participation_rate >= 0.6 and iplc_approval_rate >= 0.6
        }
    
    def _finalize_proposal(self, proposal_id: str) -> QuorumDecision:
        """Internal method to finalize a proposal decision."""
        proposal = self.proposals[proposal_id]
        vote_counts = self._count_votes(proposal_id)
        eligible_voters = self._get_eligible_voters(proposal_id)
        
        # Check quorum
        quorum_requirement = self._get_quorum_requirement(proposal_id)
        quorum_reached = vote_counts['total_votes'] >= quorum_requirement
        
        # Check approval threshold
        approval_threshold_met = False
        if vote_counts['total_votes'] > 0:
            approval_rate = vote_counts['approve'] / vote_counts['total_votes']
            approval_threshold_met = approval_rate >= proposal.approval_threshold
        
        # Check IPLC veto
        iplc_status = self.get_iplc_consensus_status(proposal_id)
        iplc_vetoed = self.iplc_veto_enabled and iplc_status['iplc_veto_triggered']
        
        # Determine decision
        if iplc_vetoed:
            decision = "rejected_iplc_veto"
            decision_rationale = "Proposal rejected due to IPLC veto"
        elif not quorum_reached:
            decision = "insufficient_quorum"
            decision_rationale = f"Insufficient quorum: {vote_counts['total_votes']}/{quorum_requirement}"
        elif approval_threshold_met:
            decision = "approved"
            decision_rationale = f"Proposal approved with {vote_counts['approve']}/{vote_counts['total_votes']} votes"
        else:
            decision = "rejected"
            decision_rationale = f"Proposal rejected with {vote_counts['approve']}/{vote_counts['total_votes']} votes"
        
        # Create decision record
        quorum_decision = QuorumDecision(
            proposal_id=proposal_id,
            decision=decision,
            total_eligible_voters=len(eligible_voters),
            total_votes_cast=vote_counts['total_votes'],
            approval_votes=vote_counts['approve'],
            rejection_votes=vote_counts['reject'],
            abstain_votes=vote_counts['abstain'],
            quorum_reached=quorum_reached,
            approval_threshold_met=approval_threshold_met,
            decision_timestamp=self._current_timestamp(),
            participating_stakeholders=[vote.voter_id for vote in proposal.votes]
        )
        
        # Update proposal
        proposal.status = "finalized"
        proposal.decision_rationale = decision_rationale
        
        # Store decision
        self.decisions[proposal_id] = quorum_decision
        
        logger.info(f"Proposal {proposal_id} finalized: {decision}")
        return quorum_decision
    
    def _count_votes(self, proposal_id: str) -> Dict[str, int]:
        """Count votes for a proposal."""
        proposal = self.proposals[proposal_id]
        
        counts = {'approve': 0, 'reject': 0, 'abstain': 0, 'total_votes': 0}
        
        for vote in proposal.votes:
            if vote.vote == VoteType.APPROVE:
                counts['approve'] += 1
            elif vote.vote == VoteType.REJECT:
                counts['reject'] += 1
            elif vote.vote == VoteType.ABSTAIN:
                counts['abstain'] += 1
            counts['total_votes'] += 1
        
        return counts
    
    def _get_eligible_voters(self, proposal_id: str) -> List[str]:
        """Get list of eligible voters for a proposal."""
        # All active stakeholders are eligible
        return [s_id for s_id, s in self.stakeholders.items() if s.is_active]
    
    def _get_quorum_requirement(self, proposal_id: str) -> int:
        """Calculate quorum requirement for a proposal."""
        proposal = self.proposals[proposal_id]
        eligible_voters = self._get_eligible_voters(proposal_id)
        return int(len(eligible_voters) * proposal.quorum_threshold)
    
    def _check_iplc_consensus(self, proposal_id: str) -> bool:
        """Check if IPLC consensus has been reached."""
        iplc_status = self.get_iplc_consensus_status(proposal_id)
        return iplc_status['iplc_consensus_reached']
    
    def _should_trigger_early_decision(self, proposal_id: str) -> bool:
        """Check if quorum sensing should trigger early decision."""
        proposal = self.proposals[proposal_id]
        vote_counts = self._count_votes(proposal_id)
        eligible_voters = self._get_eligible_voters(proposal_id)
        
        # Early decision if overwhelming majority
        total_eligible = len(eligible_voters)
        if vote_counts['total_votes'] >= total_eligible * 0.8:  # 80% participation
            approval_rate = vote_counts['approve'] / vote_counts['total_votes']
            if approval_rate >= 0.8 or approval_rate <= 0.2:  # 80% consensus either way
                return True
        
        return False
    
    def _emit_quorum_signal(self, proposal_id: str, signal_type: str):
        """Emit quorum sensing signal (placeholder for future implementation)."""
        logger.debug(f"Quorum signal emitted for {proposal_id}: {signal_type}")
    
    def _is_iplc_related_asset(self, asset_id: str) -> bool:
        """Check if an asset is related to IPLC communities."""
        # This would integrate with the blockchain to check asset metadata
        # For now, return True for demonstration
        return True
    
    def _generate_proposal_id(self, proposer_id: str, title: str) -> str:
        """Generate unique proposal ID."""
        content = f"{proposer_id}_{title}_{self._current_timestamp()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _current_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())
    
    def _add_days_to_timestamp(self, timestamp: str, days: int) -> str:
        """Add days to a timestamp."""
        import datetime
        dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        dt += datetime.timedelta(days=days)
        return dt.isoformat().replace('+00:00', 'Z')
    
    def _calculate_time_remaining(self, expires_at: str) -> str:
        """Calculate time remaining until expiration."""
        import datetime
        now = datetime.datetime.fromisoformat(self._current_timestamp())
        expires = datetime.datetime.fromisoformat(expires_at.replace('Z', ''))
        remaining = expires - now
        
        if remaining.total_seconds() <= 0:
            return "Expired"
        
        days = remaining.days
        hours = remaining.seconds // 3600
        return f"{days}d {hours}h remaining"
    
    def _sign_vote(self, vote_data: Dict, voter_id: str) -> str:
        """Sign vote data (simplified implementation)."""
        # In real implementation, would use private key cryptographic signing
        content = json.dumps(vote_data, sort_keys=True)
        signature = hashlib.sha256(f"{voter_id}_{content}".encode()).hexdigest()
        return signature
    
    def _resolve_delegation_chain(self, from_voter: str, to_voter: str) -> List[str]:
        """Resolve delegation chain to prevent cycles."""
        # Simplified implementation - in practice would handle complex delegation
        return [from_voter, to_voter]
    
    def _update_reputation(self, voter_id: str, proposal_id: str, vote: VoteType):
        """Update stakeholder reputation based on voting patterns."""
        # Simplified reputation update
        stakeholder = self.stakeholders[voter_id]
        if vote != VoteType.ABSTAIN:
            stakeholder.reputation_score = min(stakeholder.reputation_score + 0.01, 2.0)


def main():
    """Example usage of the QuorumGovernance system."""
    # Initialize governance system
    governance = QuorumGovernance()
    
    # Register stakeholders
    print("Registering stakeholders...")
    
    # IPLC representatives
    iplc1 = governance.register_stakeholder(
        "iplc_001", "Kayapó Representative", StakeholderType.IPLC_REPRESENTATIVE,
        community_affiliation="Kayapó Indigenous Territory"
    )
    iplc2 = governance.register_stakeholder(
        "iplc_002", "Maasai Representative", StakeholderType.IPLC_REPRESENTATIVE,
        community_affiliation="Maasai Community"
    )
    
    # Other stakeholders
    researcher = governance.register_stakeholder(
        "researcher_001", "Dr. Jane Smith", StakeholderType.RESEARCHER
    )
    industry = governance.register_stakeholder(
        "industry_001", "PharmaCorp Representative", StakeholderType.INDUSTRY
    )
    
    # Submit a benefit-sharing proposal
    print("\nSubmitting benefit-sharing proposal...")
    proposal_id = governance.submit_proposal(
        proposer_id="industry_001",
        title="COVID-19 Vaccine Benefit Sharing",
        description="Proposal to share 1% of vaccine revenues with source communities",
        proposal_type=ProposalType.BENEFIT_SHARING_APPROVAL,
        dsi_asset_ids=["NC_045512.2"],
        proposed_terms={
            "revenue_share_percentage": 0.01,
            "minimum_payment": 1000000,
            "distribution_method": "direct_transfer"
        }
    )
    
    # Cast votes
    print("\nCasting votes...")
    governance.cast_vote("iplc_001", proposal_id, VoteType.APPROVE, 
                        "Supports fair benefit sharing")
    governance.cast_vote("iplc_002", proposal_id, VoteType.APPROVE, 
                        "Agrees with proposal terms")
    governance.cast_vote("researcher_001", proposal_id, VoteType.APPROVE, 
                        "Supports equitable sharing")
    governance.cast_vote("industry_001", proposal_id, VoteType.APPROVE, 
                        "Committed to fair practices")
    
    # Check proposal status
    print("\nChecking proposal status...")
    status = governance.check_proposal_status(proposal_id)
    print(f"Proposal: {status['title']}")
    print(f"Status: {status['status']}")
    print(f"Votes: {status['vote_counts']}")
    print(f"Quorum reached: {status['quorum_reached']}")
    
    # Check IPLC consensus
    print("\nChecking IPLC consensus...")
    iplc_status = governance.get_iplc_consensus_status(proposal_id)
    print(f"IPLC participation: {iplc_status['iplc_participation_rate']:.2%}")
    print(f"IPLC approval rate: {iplc_status['iplc_approval_rate']:.2%}")
    print(f"IPLC consensus reached: {iplc_status['iplc_consensus_reached']}")
    
    # Finalize proposal
    print("\nFinalizing proposal...")
    decision = governance.finalize_proposal(proposal_id)
    print(f"Final decision: {decision.decision}")
    print(f"Total votes: {decision.total_votes_cast}/{decision.total_eligible_voters}")
    print(f"Approval votes: {decision.approval_votes}")


if __name__ == "__main__":
    main()
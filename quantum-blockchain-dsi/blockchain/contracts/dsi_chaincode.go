package main

import (
	"encoding/json"
	"fmt"
	"strconv"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// DSIChaincode implements the smart contract for DSI benefit allocation
type DSIChaincode struct {
	contractapi.Contract
}

// DSIAsset represents a Digital Sequence Information asset
type DSIAsset struct {
	ID                    string              `json:"id"`
	SequenceID           string              `json:"sequence_id"`
	DOI                  string              `json:"doi"`
	SourceCommunity      string              `json:"source_community"`
	IPLCConsent          bool                `json:"iplc_consent"`
	AccessTerms          string              `json:"access_terms"`
	BenefitSharingRate   float64             `json:"benefit_sharing_rate"`
	Metadata             map[string]interface{} `json:"metadata"`
	CreatedAt            time.Time           `json:"created_at"`
	UpdatedAt            time.Time           `json:"updated_at"`
	Status               string              `json:"status"`
	UsageHistory         []UsageRecord       `json:"usage_history"`
}

// UsageRecord tracks DSI usage for benefit allocation
type UsageRecord struct {
	UsageID        string    `json:"usage_id"`
	UserID         string    `json:"user_id"`
	Organization   string    `json:"organization"`
	Purpose        string    `json:"purpose"`
	CommercialUse  bool      `json:"commercial_use"`
	Revenue        float64   `json:"revenue"`
	BenefitAmount  float64   `json:"benefit_amount"`
	Timestamp      time.Time `json:"timestamp"`
	Attribution    map[string]float64 `json:"attribution"`
}

// BenefitAllocation represents payment to Cali Fund
type BenefitAllocation struct {
	AllocationID   string              `json:"allocation_id"`
	DSIAssets      []string            `json:"dsi_assets"`
	TotalAmount    float64             `json:"total_amount"`
	Recipients     map[string]float64  `json:"recipients"`
	Status         string              `json:"status"`
	Timestamp      time.Time           `json:"timestamp"`
	TransactionHash string             `json:"transaction_hash"`
}

// GovernanceProposal for quorum sensing decisions
type GovernanceProposal struct {
	ProposalID      string            `json:"proposal_id"`
	Type            string            `json:"type"`
	Description     string            `json:"description"`
	Proposer        string            `json:"proposer"`
	DSIAssetID      string            `json:"dsi_asset_id"`
	Votes           map[string]string `json:"votes"` // voter_id -> vote (approve/reject)
	QuorumThreshold float64           `json:"quorum_threshold"`
	Status          string            `json:"status"`
	CreatedAt       time.Time         `json:"created_at"`
	ExpiresAt       time.Time         `json:"expires_at"`
}

// InitLedger initializes the chaincode with sample data
func (s *DSIChaincode) InitLedger(ctx contractapi.TransactionContextInterface) error {
	// Initialize with sample IPLC-consented DSI asset
	sampleDSI := DSIAsset{
		ID:                 "dsi_001",
		SequenceID:         "NC_045512.2",
		DOI:                "10.5061/dryad.123456",
		SourceCommunity:    "Kayapó Indigenous Territory",
		IPLCConsent:        true,
		AccessTerms:        "Prior informed consent required; 1% revenue sharing",
		BenefitSharingRate: 0.01,
		Metadata: map[string]interface{}{
			"@context":     "https://schema.org/",
			"@type":        "Dataset",
			"name":         "SARS-CoV-2 genome sequence",
			"description":  "Complete genome sequence from traditional medicinal plant",
			"keywords":     []string{"genomics", "traditional knowledge", "medicinal plants"},
			"license":      "CC-BY-NC-SA",
			"provider":     "Kayapó Indigenous Community",
			"dateCreated":  "2024-01-15",
			"isAccessibleForFree": false,
		},
		CreatedAt:    time.Now(),
		UpdatedAt:    time.Now(),
		Status:       "active",
		UsageHistory: []UsageRecord{},
	}

	assetJSON, err := json.Marshal(sampleDSI)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(sampleDSI.ID, assetJSON)
}

// RegisterDSI creates a new DSI asset with FAIR-CARE compliance
func (s *DSIChaincode) RegisterDSI(ctx contractapi.TransactionContextInterface, 
	id string, sequenceID string, doi string, sourceCommunity string, 
	ipLCConsent bool, accessTerms string, benefitSharingRate float64,
	metadataJSON string) error {

	// Parse metadata
	var metadata map[string]interface{}
	err := json.Unmarshal([]byte(metadataJSON), &metadata)
	if err != nil {
		return fmt.Errorf("failed to parse metadata: %v", err)
	}

	// Validate CARE compliance
	if !ipLCConsent && sourceCommunity != "" {
		return fmt.Errorf("IPLC consent required for community-sourced DSI")
	}

	// Create DSI asset
	dsiAsset := DSIAsset{
		ID:                 id,
		SequenceID:         sequenceID,
		DOI:                doi,
		SourceCommunity:    sourceCommunity,
		IPLCConsent:        ipLCConsent,
		AccessTerms:        accessTerms,
		BenefitSharingRate: benefitSharingRate,
		Metadata:           metadata,
		CreatedAt:          time.Now(),
		UpdatedAt:          time.Now(),
		Status:             "active",
		UsageHistory:       []UsageRecord{},
	}

	assetJSON, err := json.Marshal(dsiAsset)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(id, assetJSON)
}

// GetDSI retrieves a DSI asset by ID
func (s *DSIChaincode) GetDSI(ctx contractapi.TransactionContextInterface, id string) (*DSIAsset, error) {
	assetJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("failed to read from world state: %v", err)
	}
	if assetJSON == nil {
		return nil, fmt.Errorf("DSI asset %s does not exist", id)
	}

	var asset DSIAsset
	err = json.Unmarshal(assetJSON, &asset)
	if err != nil {
		return nil, err
	}

	return &asset, nil
}

// RecordUsage logs DSI usage for benefit tracking
func (s *DSIChaincode) RecordUsage(ctx contractapi.TransactionContextInterface,
	dsiID string, usageID string, userID string, organization string,
	purpose string, commercialUse bool, revenue float64,
	attributionJSON string) error {

	// Get existing DSI asset
	asset, err := s.GetDSI(ctx, dsiID)
	if err != nil {
		return err
	}

	// Check access permissions
	if asset.SourceCommunity != "" && !asset.IPLCConsent {
		return fmt.Errorf("access denied: IPLC consent required")
	}

	// Parse attribution weights
	var attribution map[string]float64
	err = json.Unmarshal([]byte(attributionJSON), &attribution)
	if err != nil {
		return fmt.Errorf("failed to parse attribution: %v", err)
	}

	// Calculate benefit amount
	benefitAmount := revenue * asset.BenefitSharingRate

	// Create usage record
	usageRecord := UsageRecord{
		UsageID:       usageID,
		UserID:        userID,
		Organization:  organization,
		Purpose:       purpose,
		CommercialUse: commercialUse,
		Revenue:       revenue,
		BenefitAmount: benefitAmount,
		Timestamp:     time.Now(),
		Attribution:   attribution,
	}

	// Update asset
	asset.UsageHistory = append(asset.UsageHistory, usageRecord)
	asset.UpdatedAt = time.Now()

	// Save updated asset
	assetJSON, err := json.Marshal(asset)
	if err != nil {
		return err
	}

	err = ctx.GetStub().PutState(dsiID, assetJSON)
	if err != nil {
		return err
	}

	// Trigger benefit allocation if commercial use
	if commercialUse && benefitAmount > 0 {
		return s.allocateBenefits(ctx, dsiID, benefitAmount, attribution)
	}

	return nil
}

// allocateBenefits processes benefit distribution to Cali Fund
func (s *DSIChaincode) allocateBenefits(ctx contractapi.TransactionContextInterface,
	dsiID string, amount float64, attribution map[string]float64) error {

	allocationID := fmt.Sprintf("alloc_%s_%d", dsiID, time.Now().Unix())

	// Calculate recipient shares based on attribution
	recipients := make(map[string]float64)
	for source, weight := range attribution {
		recipients[source] = amount * weight
	}

	allocation := BenefitAllocation{
		AllocationID:   allocationID,
		DSIAssets:      []string{dsiID},
		TotalAmount:    amount,
		Recipients:     recipients,
		Status:         "pending",
		Timestamp:      time.Now(),
		TransactionHash: "", // Will be set after blockchain confirmation
	}

	allocationJSON, err := json.Marshal(allocation)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(allocationID, allocationJSON)
}

// SubmitGovernanceProposal creates a new governance proposal
func (s *DSIChaincode) SubmitGovernanceProposal(ctx contractapi.TransactionContextInterface,
	proposalID string, proposalType string, description string,
	proposer string, dsiAssetID string, quorumThreshold float64) error {

	proposal := GovernanceProposal{
		ProposalID:      proposalID,
		Type:            proposalType,
		Description:     description,
		Proposer:        proposer,
		DSIAssetID:      dsiAssetID,
		Votes:           make(map[string]string),
		QuorumThreshold: quorumThreshold,
		Status:          "active",
		CreatedAt:       time.Now(),
		ExpiresAt:       time.Now().Add(7 * 24 * time.Hour), // 7 days
	}

	proposalJSON, err := json.Marshal(proposal)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(proposalID, proposalJSON)
}

// VoteOnProposal allows stakeholders to vote on governance proposals
func (s *DSIChaincode) VoteOnProposal(ctx contractapi.TransactionContextInterface,
	proposalID string, voterID string, vote string) error {

	proposalJSON, err := ctx.GetStub().GetState(proposalID)
	if err != nil {
		return fmt.Errorf("failed to read proposal: %v", err)
	}
	if proposalJSON == nil {
		return fmt.Errorf("proposal %s does not exist", proposalID)
	}

	var proposal GovernanceProposal
	err = json.Unmarshal(proposalJSON, &proposal)
	if err != nil {
		return err
	}

	// Check if proposal is still active
	if proposal.Status != "active" || time.Now().After(proposal.ExpiresAt) {
		return fmt.Errorf("proposal is no longer active")
	}

	// Validate vote
	if vote != "approve" && vote != "reject" {
		return fmt.Errorf("invalid vote: must be 'approve' or 'reject'")
	}

	// Record vote
	proposal.Votes[voterID] = vote

	// Check if quorum reached
	totalVotes := len(proposal.Votes)
	approvalCount := 0
	for _, v := range proposal.Votes {
		if v == "approve" {
			approvalCount++
		}
	}

	// Assuming total eligible voters is 10 for demonstration
	totalEligibleVoters := 10
	quorumReached := float64(totalVotes) >= (proposal.QuorumThreshold * float64(totalEligibleVoters))

	if quorumReached {
		approvalRate := float64(approvalCount) / float64(totalVotes)
		if approvalRate > 0.5 { // Simple majority
			proposal.Status = "approved"
		} else {
			proposal.Status = "rejected"
		}
	}

	// Save updated proposal
	updatedProposalJSON, err := json.Marshal(proposal)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(proposalID, updatedProposalJSON)
}

// GetAllDSI returns all DSI assets
func (s *DSIChaincode) GetAllDSI(ctx contractapi.TransactionContextInterface) ([]*DSIAsset, error) {
	resultsIterator, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()

	var assets []*DSIAsset
	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}

		var asset DSIAsset
		err = json.Unmarshal(queryResponse.Value, &asset)
		if err == nil {
			assets = append(assets, &asset)
		}
	}

	return assets, nil
}

// UpdateIPLCConsent allows updating Indigenous consent status
func (s *DSIChaincode) UpdateIPLCConsent(ctx contractapi.TransactionContextInterface,
	dsiID string, consent bool, updatedBy string) error {

	asset, err := s.GetDSI(ctx, dsiID)
	if err != nil {
		return err
	}

	// Only allow updates by authorized IPLC representatives
	// In a real implementation, this would check cryptographic signatures
	asset.IPLCConsent = consent
	asset.UpdatedAt = time.Now()

	assetJSON, err := json.Marshal(asset)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(dsiID, assetJSON)
}

func main() {
	chaincode, err := contractapi.NewChaincode(&DSIChaincode{})
	if err != nil {
		fmt.Printf("Error creating DSI chaincode: %s", err.Error())
		return
	}

	if err := chaincode.Start(); err != nil {
		fmt.Printf("Error starting DSI chaincode: %s", err.Error())
	}
}
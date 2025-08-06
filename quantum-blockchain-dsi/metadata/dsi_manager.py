"""
FAIR-CARE Compliant DSI Metadata Management System

This module implements metadata management for Digital Sequence Information (DSI)
that complies with both FAIR (Findable, Accessible, Interoperable, Reusable) and
CARE (Collective benefit, Authority to control, Responsibility, Ethics) principles.
"""

import json
import uuid
import datetime
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from jsonschema import validate, ValidationError
import rdflib
from rdflib import Graph, Literal, BNode, Namespace, RDF, RDFS, URIRef
from pyld import jsonld
import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define namespaces for RDF
SCHEMA = Namespace("https://schema.org/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
CARE = Namespace("https://care-principles.org/")
DSI = Namespace("https://dsi-governance.org/")
DOI = Namespace("https://doi.org/")


@dataclass
class IPLCConsent:
    """Represents Indigenous consent information."""
    community_name: str
    consent_given: bool
    consent_date: str
    consent_expires: Optional[str]
    consent_scope: List[str]  # e.g., ["research", "commercial"]
    restrictions: List[str]
    contact_person: str
    consent_document_hash: Optional[str] = None
    revocation_process: Optional[str] = None


@dataclass
class FAIRMetadata:
    """FAIR-compliant metadata structure."""
    # Findable
    identifier: str  # DOI or other persistent identifier
    title: str
    description: str
    keywords: List[str]
    creators: List[Dict[str, str]]
    
    # Accessible
    access_url: str
    license: str
    access_rights: str
    download_url: Optional[str] = None
    
    # Interoperable
    format: str  # MIME type
    standards: List[str]  # Metadata standards used
    vocabulary: List[str]  # Controlled vocabularies
    
    # Reusable
    provenance: Dict[str, Any]
    usage_notes: str
    citation: str
    version: str = "1.0"


@dataclass
class CAREMetadata:
    """CARE-compliant metadata structure."""
    # Collective Benefit
    community_benefits: List[str]
    benefit_sharing_terms: Dict[str, Any]
    community_participation: bool
    
    # Authority to Control
    governance_structure: Dict[str, Any]
    consent_requirements: IPLCConsent
    data_sovereignty_assertions: List[str]
    
    # Responsibility
    ethical_review_status: str
    cultural_protocols: List[str]
    researcher_responsibilities: List[str]
    
    # Ethics
    ethical_considerations: List[str]
    cultural_sensitivity: Dict[str, Any]
    future_use_considerations: List[str]


@dataclass
class DSIAssetMetadata:
    """Complete DSI asset metadata combining FAIR and CARE."""
    # Core identifiers
    dsi_id: str
    sequence_id: str  # e.g., GenBank accession
    doi: str
    
    # FAIR metadata
    fair: FAIRMetadata
    
    # CARE metadata
    care: CAREMetadata
    
    # Technical metadata
    sequence_type: str  # DNA, RNA, protein
    sequence_length: int
    organism: str
    tissue_type: Optional[str]
    collection_date: str
    collection_location: Dict[str, float]  # lat, lon
    
    # Governance metadata
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


class DSIMetadataManager:
    """
    Manager for FAIR-CARE compliant DSI metadata.
    
    Handles creation, validation, storage, and retrieval of DSI metadata
    with full compliance to both FAIR and CARE principles.
    """
    
    def __init__(self, database_path: str = "dsi_metadata.db"):
        """
        Initialize the metadata manager.
        
        Args:
            database_path: Path to SQLite database for metadata storage
        """
        self.database_path = database_path
        self._init_database()
        self._load_schemas()
        
        # Initialize RDF graph for linked data
        self.graph = Graph()
        self._bind_namespaces()
        
        logger.info("DSI Metadata Manager initialized")
    
    def _init_database(self):
        """Initialize SQLite database for metadata storage."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Create metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dsi_metadata (
                dsi_id TEXT PRIMARY KEY,
                sequence_id TEXT NOT NULL,
                doi TEXT UNIQUE,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Create consent table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iplc_consent (
                consent_id TEXT PRIMARY KEY,
                dsi_id TEXT NOT NULL,
                community_name TEXT NOT NULL,
                consent_given BOOLEAN NOT NULL,
                consent_date TEXT NOT NULL,
                consent_expires TEXT,
                consent_scope TEXT NOT NULL,
                restrictions TEXT,
                contact_person TEXT NOT NULL,
                consent_document_hash TEXT,
                revocation_process TEXT,
                FOREIGN KEY (dsi_id) REFERENCES dsi_metadata (dsi_id)
            )
        ''')
        
        # Create access log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_log (
                log_id TEXT PRIMARY KEY,
                dsi_id TEXT NOT NULL,
                accessor_id TEXT NOT NULL,
                access_type TEXT NOT NULL,
                access_timestamp TEXT NOT NULL,
                purpose TEXT,
                approved BOOLEAN NOT NULL,
                FOREIGN KEY (dsi_id) REFERENCES dsi_metadata (dsi_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_schemas(self):
        """Load JSON schemas for validation."""
        self.fair_schema = {
            "type": "object",
            "required": ["identifier", "title", "description", "creators", "license"],
            "properties": {
                "identifier": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "creators": {"type": "array"},
                "access_url": {"type": "string", "format": "uri"},
                "license": {"type": "string"},
                "access_rights": {"type": "string"},
                "format": {"type": "string"},
                "standards": {"type": "array"},
                "vocabulary": {"type": "array"},
                "provenance": {"type": "object"},
                "usage_notes": {"type": "string"},
                "citation": {"type": "string"},
                "version": {"type": "string"}
            }
        }
        
        self.care_schema = {
            "type": "object",
            "required": ["consent_requirements", "ethical_review_status"],
            "properties": {
                "community_benefits": {"type": "array"},
                "benefit_sharing_terms": {"type": "object"},
                "community_participation": {"type": "boolean"},
                "governance_structure": {"type": "object"},
                "consent_requirements": {"type": "object"},
                "data_sovereignty_assertions": {"type": "array"},
                "ethical_review_status": {"type": "string"},
                "cultural_protocols": {"type": "array"},
                "researcher_responsibilities": {"type": "array"},
                "ethical_considerations": {"type": "array"},
                "cultural_sensitivity": {"type": "object"},
                "future_use_considerations": {"type": "array"}
            }
        }
    
    def _bind_namespaces(self):
        """Bind RDF namespaces to the graph."""
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("care", CARE)
        self.graph.bind("dsi", DSI)
        self.graph.bind("doi", DOI)
    
    def create_dsi_metadata(self,
                          sequence_id: str,
                          sequence_data: str,
                          organism: str,
                          collection_info: Dict[str, Any],
                          fair_metadata: Dict[str, Any],
                          care_metadata: Dict[str, Any],
                          created_by: str) -> DSIAssetMetadata:
        """
        Create comprehensive DSI metadata.
        
        Args:
            sequence_id: GenBank or other sequence identifier
            sequence_data: The actual sequence data
            organism: Source organism
            collection_info: Collection metadata (date, location, etc.)
            fair_metadata: FAIR-compliant metadata
            care_metadata: CARE-compliant metadata
            created_by: Creator identifier
            
        Returns:
            Complete DSI metadata object
        """
        # Generate identifiers
        dsi_id = str(uuid.uuid4())
        doi = self._generate_doi(dsi_id)
        
        # Validate FAIR metadata
        try:
            validate(instance=fair_metadata, schema=self.fair_schema)
        except ValidationError as e:
            raise ValueError(f"FAIR metadata validation failed: {e}")
        
        # Validate CARE metadata
        try:
            validate(instance=care_metadata, schema=self.care_schema)
        except ValidationError as e:
            raise ValueError(f"CARE metadata validation failed: {e}")
        
        # Create FAIR metadata object
        fair = FAIRMetadata(
            identifier=doi,
            title=fair_metadata["title"],
            description=fair_metadata["description"],
            keywords=fair_metadata.get("keywords", []),
            creators=fair_metadata["creators"],
            access_url=fair_metadata.get("access_url", f"https://dsi-platform.org/{dsi_id}"),
            license=fair_metadata["license"],
            access_rights=fair_metadata.get("access_rights", "Restricted"),
            download_url=fair_metadata.get("download_url"),
            format=fair_metadata.get("format", "application/json"),
            standards=fair_metadata.get("standards", ["FAIR", "CARE"]),
            vocabulary=fair_metadata.get("vocabulary", ["schema.org", "dublin-core"]),
            provenance=fair_metadata.get("provenance", {}),
            usage_notes=fair_metadata.get("usage_notes", ""),
            citation=fair_metadata.get("citation", ""),
            version=fair_metadata.get("version", "1.0")
        )
        
        # Create IPLC consent object
        consent_info = care_metadata["consent_requirements"]
        iplc_consent = IPLCConsent(
            community_name=consent_info["community_name"],
            consent_given=consent_info["consent_given"],
            consent_date=consent_info["consent_date"],
            consent_expires=consent_info.get("consent_expires"),
            consent_scope=consent_info.get("consent_scope", []),
            restrictions=consent_info.get("restrictions", []),
            contact_person=consent_info["contact_person"],
            consent_document_hash=consent_info.get("consent_document_hash"),
            revocation_process=consent_info.get("revocation_process")
        )
        
        # Create CARE metadata object
        care = CAREMetadata(
            community_benefits=care_metadata.get("community_benefits", []),
            benefit_sharing_terms=care_metadata.get("benefit_sharing_terms", {}),
            community_participation=care_metadata.get("community_participation", False),
            governance_structure=care_metadata.get("governance_structure", {}),
            consent_requirements=iplc_consent,
            data_sovereignty_assertions=care_metadata.get("data_sovereignty_assertions", []),
            ethical_review_status=care_metadata["ethical_review_status"],
            cultural_protocols=care_metadata.get("cultural_protocols", []),
            researcher_responsibilities=care_metadata.get("researcher_responsibilities", []),
            ethical_considerations=care_metadata.get("ethical_considerations", []),
            cultural_sensitivity=care_metadata.get("cultural_sensitivity", {}),
            future_use_considerations=care_metadata.get("future_use_considerations", [])
        )
        
        # Create complete metadata
        metadata = DSIAssetMetadata(
            dsi_id=dsi_id,
            sequence_id=sequence_id,
            doi=doi,
            fair=fair,
            care=care,
            sequence_type=collection_info.get("sequence_type", "DNA"),
            sequence_length=len(sequence_data),
            organism=organism,
            tissue_type=collection_info.get("tissue_type"),
            collection_date=collection_info["collection_date"],
            collection_location=collection_info["collection_location"],
            created_by=created_by
        )
        
        # Store in database
        self._store_metadata(metadata)
        
        # Add to RDF graph
        self._add_to_rdf_graph(metadata)
        
        # Log creation
        self._log_access(dsi_id, created_by, "create", "DSI metadata created", approved=True)
        
        logger.info(f"Created DSI metadata for {sequence_id} (ID: {dsi_id})")
        return metadata
    
    def get_dsi_metadata(self, dsi_id: str) -> Optional[DSIAssetMetadata]:
        """
        Retrieve DSI metadata by ID.
        
        Args:
            dsi_id: DSI identifier
            
        Returns:
            DSI metadata object or None if not found
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT metadata_json FROM dsi_metadata WHERE dsi_id = ? AND status = 'active'",
            (dsi_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            metadata_dict = json.loads(result[0])
            return self._dict_to_metadata(metadata_dict)
        
        return None
    
    def search_dsi_metadata(self,
                          query: Dict[str, Any],
                          include_restricted: bool = False) -> List[DSIAssetMetadata]:
        """
        Search DSI metadata based on query parameters.
        
        Args:
            query: Search parameters (organism, keywords, etc.)
            include_restricted: Whether to include restricted access data
            
        Returns:
            List of matching DSI metadata objects
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Build search query
        where_clauses = ["status = 'active'"]
        params = []
        
        if "organism" in query:
            where_clauses.append("JSON_EXTRACT(metadata_json, '$.organism') LIKE ?")
            params.append(f"%{query['organism']}%")
        
        if "sequence_type" in query:
            where_clauses.append("JSON_EXTRACT(metadata_json, '$.sequence_type') = ?")
            params.append(query["sequence_type"])
        
        if "keywords" in query:
            # Search in FAIR keywords
            keywords_query = " OR ".join([
                "JSON_EXTRACT(metadata_json, '$.fair.keywords') LIKE ?" 
                for _ in query["keywords"]
            ])
            where_clauses.append(f"({keywords_query})")
            params.extend([f'%{keyword}%' for keyword in query["keywords"]])
        
        sql_query = f"""
            SELECT metadata_json FROM dsi_metadata 
            WHERE {' AND '.join(where_clauses)}
        """
        
        cursor.execute(sql_query, params)
        results = cursor.fetchall()
        conn.close()
        
        metadata_list = []
        for result in results:
            metadata_dict = json.loads(result[0])
            metadata = self._dict_to_metadata(metadata_dict)
            
            # Check access rights
            if not include_restricted and metadata.fair.access_rights == "Restricted":
                # Check if IPLC consent allows access
                if not metadata.care.consent_requirements.consent_given:
                    continue
            
            metadata_list.append(metadata)
        
        return metadata_list
    
    def update_iplc_consent(self,
                          dsi_id: str,
                          consent_updates: Dict[str, Any],
                          updated_by: str) -> bool:
        """
        Update IPLC consent information.
        
        Args:
            dsi_id: DSI identifier
            consent_updates: Updated consent information
            updated_by: Who is making the update
            
        Returns:
            True if update successful
        """
        metadata = self.get_dsi_metadata(dsi_id)
        if not metadata:
            raise ValueError(f"DSI {dsi_id} not found")
        
        # Verify authority to update (should be IPLC representative)
        if not self._verify_iplc_authority(updated_by, metadata.care.consent_requirements.community_name):
            raise PermissionError("Only IPLC representatives can update consent")
        
        # Update consent information
        consent = metadata.care.consent_requirements
        for key, value in consent_updates.items():
            if hasattr(consent, key):
                setattr(consent, key, value)
        
        metadata.updated_at = datetime.datetime.utcnow().isoformat()
        
        # Store updated metadata
        self._store_metadata(metadata)
        
        # Update RDF graph
        self._update_rdf_graph(metadata)
        
        # Log update
        self._log_access(dsi_id, updated_by, "consent_update", 
                        f"IPLC consent updated: {list(consent_updates.keys())}", approved=True)
        
        logger.info(f"Updated IPLC consent for {dsi_id}")
        return True
    
    def check_access_permissions(self,
                               dsi_id: str,
                               accessor_id: str,
                               access_type: str,
                               purpose: str) -> Dict[str, Any]:
        """
        Check if access to DSI is permitted.
        
        Args:
            dsi_id: DSI identifier
            accessor_id: Who is requesting access
            access_type: Type of access (view, download, commercial_use)
            purpose: Purpose of access
            
        Returns:
            Access decision with rationale
        """
        metadata = self.get_dsi_metadata(dsi_id)
        if not metadata:
            return {"permitted": False, "reason": "DSI not found"}
        
        consent = metadata.care.consent_requirements
        
        # Check basic consent
        if not consent.consent_given:
            return {"permitted": False, "reason": "IPLC consent not given"}
        
        # Check consent expiration
        if consent.consent_expires:
            expires = datetime.datetime.fromisoformat(consent.consent_expires)
            if datetime.datetime.utcnow() > expires:
                return {"permitted": False, "reason": "IPLC consent expired"}
        
        # Check consent scope
        if access_type == "commercial_use" and "commercial" not in consent.consent_scope:
            return {"permitted": False, "reason": "Commercial use not permitted"}
        
        if access_type == "research" and "research" not in consent.consent_scope:
            return {"permitted": False, "reason": "Research use not permitted"}
        
        # Check restrictions
        for restriction in consent.restrictions:
            if restriction.lower() in purpose.lower():
                return {"permitted": False, "reason": f"Restricted: {restriction}"}
        
        # Log access check
        self._log_access(dsi_id, accessor_id, f"access_check_{access_type}", purpose, approved=True)
        
        return {
            "permitted": True,
            "reason": "Access permitted under IPLC consent",
            "conditions": consent.restrictions,
            "contact": consent.contact_person
        }
    
    def generate_jsonld(self, dsi_id: str) -> Dict[str, Any]:
        """
        Generate JSON-LD representation of DSI metadata.
        
        Args:
            dsi_id: DSI identifier
            
        Returns:
            JSON-LD formatted metadata
        """
        metadata = self.get_dsi_metadata(dsi_id)
        if not metadata:
            raise ValueError(f"DSI {dsi_id} not found")
        
        # Create JSON-LD context
        context = {
            "@context": {
                "schema": "https://schema.org/",
                "dcterms": "http://purl.org/dc/terms/",
                "care": "https://care-principles.org/",
                "dsi": "https://dsi-governance.org/"
            }
        }
        
        # Build JSON-LD document
        jsonld_doc = {
            "@context": context["@context"],
            "@type": "schema:Dataset",
            "@id": metadata.fair.identifier,
            "schema:identifier": metadata.dsi_id,
            "schema:name": metadata.fair.title,
            "schema:description": metadata.fair.description,
            "schema:keywords": metadata.fair.keywords,
            "schema:creator": metadata.fair.creators,
            "schema:license": metadata.fair.license,
            "schema:url": metadata.fair.access_url,
            "schema:version": metadata.fair.version,
            "schema:dateCreated": metadata.created_at,
            "schema:dateModified": metadata.updated_at,
            "dcterms:format": metadata.fair.format,
            "dcterms:provenance": metadata.fair.provenance,
            "care:communityBenefits": metadata.care.community_benefits,
            "care:consentGiven": metadata.care.consent_requirements.consent_given,
            "care:governanceStructure": metadata.care.governance_structure,
            "care:culturalProtocols": metadata.care.cultural_protocols,
            "dsi:sequenceId": metadata.sequence_id,
            "dsi:organism": metadata.organism,
            "dsi:sequenceType": metadata.sequence_type,
            "dsi:sequenceLength": metadata.sequence_length,
            "dsi:collectionDate": metadata.collection_date,
            "dsi:collectionLocation": metadata.collection_location
        }
        
        return jsonld_doc
    
    def export_rdf(self, format: str = "turtle") -> str:
        """
        Export RDF graph in specified format.
        
        Args:
            format: RDF serialization format (turtle, xml, json-ld)
            
        Returns:
            Serialized RDF data
        """
        return self.graph.serialize(format=format)
    
    def _generate_doi(self, dsi_id: str) -> str:
        """Generate DOI for DSI asset."""
        # In practice, this would register with a DOI provider
        return f"10.5061/dsi.{dsi_id}"
    
    def _store_metadata(self, metadata: DSIAssetMetadata):
        """Store metadata in database."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(asdict(metadata), default=str)
        
        cursor.execute('''
            INSERT OR REPLACE INTO dsi_metadata 
            (dsi_id, sequence_id, doi, metadata_json, created_at, updated_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata.dsi_id,
            metadata.sequence_id,
            metadata.doi,
            metadata_json,
            metadata.created_at,
            metadata.updated_at,
            metadata.status
        ))
        
        # Store consent separately for easier querying
        consent = metadata.care.consent_requirements
        cursor.execute('''
            INSERT OR REPLACE INTO iplc_consent
            (consent_id, dsi_id, community_name, consent_given, consent_date,
             consent_expires, consent_scope, restrictions, contact_person,
             consent_document_hash, revocation_process)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            metadata.dsi_id,
            consent.community_name,
            consent.consent_given,
            consent.consent_date,
            consent.consent_expires,
            json.dumps(consent.consent_scope),
            json.dumps(consent.restrictions),
            consent.contact_person,
            consent.consent_document_hash,
            consent.revocation_process
        ))
        
        conn.commit()
        conn.close()
    
    def _add_to_rdf_graph(self, metadata: DSIAssetMetadata):
        """Add metadata to RDF graph."""
        # Create subject URI
        subject = URIRef(metadata.fair.identifier)
        
        # Add basic metadata
        self.graph.add((subject, RDF.type, SCHEMA.Dataset))
        self.graph.add((subject, SCHEMA.identifier, Literal(metadata.dsi_id)))
        self.graph.add((subject, SCHEMA.name, Literal(metadata.fair.title)))
        self.graph.add((subject, SCHEMA.description, Literal(metadata.fair.description)))
        self.graph.add((subject, SCHEMA.license, Literal(metadata.fair.license)))
        
        # Add CARE-specific metadata
        self.graph.add((subject, CARE.consentGiven, 
                       Literal(metadata.care.consent_requirements.consent_given)))
        self.graph.add((subject, CARE.communityName, 
                       Literal(metadata.care.consent_requirements.community_name)))
        
        # Add DSI-specific metadata
        self.graph.add((subject, DSI.sequenceId, Literal(metadata.sequence_id)))
        self.graph.add((subject, DSI.organism, Literal(metadata.organism)))
        self.graph.add((subject, DSI.sequenceType, Literal(metadata.sequence_type)))
    
    def _update_rdf_graph(self, metadata: DSIAssetMetadata):
        """Update RDF graph with new metadata."""
        # Remove existing triples for this subject
        subject = URIRef(metadata.fair.identifier)
        self.graph.remove((subject, None, None))
        
        # Add updated metadata
        self._add_to_rdf_graph(metadata)
    
    def _dict_to_metadata(self, metadata_dict: Dict[str, Any]) -> DSIAssetMetadata:
        """Convert dictionary to DSIAssetMetadata object."""
        # Convert nested dictionaries to dataclass objects
        fair_dict = metadata_dict["fair"]
        care_dict = metadata_dict["care"]
        consent_dict = care_dict["consent_requirements"]
        
        # Create objects
        consent = IPLCConsent(**consent_dict)
        care_dict["consent_requirements"] = consent
        fair = FAIRMetadata(**fair_dict)
        care = CAREMetadata(**care_dict)
        
        # Update main metadata
        metadata_dict["fair"] = fair
        metadata_dict["care"] = care
        
        return DSIAssetMetadata(**metadata_dict)
    
    def _log_access(self, dsi_id: str, accessor_id: str, access_type: str, 
                   purpose: str, approved: bool):
        """Log access attempt."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO access_log
            (log_id, dsi_id, accessor_id, access_type, access_timestamp, purpose, approved)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            dsi_id,
            accessor_id,
            access_type,
            datetime.datetime.utcnow().isoformat(),
            purpose,
            approved
        ))
        
        conn.commit()
        conn.close()
    
    def _verify_iplc_authority(self, user_id: str, community_name: str) -> bool:
        """Verify if user has authority to update IPLC consent."""
        # In practice, this would check against IPLC governance records
        # For demonstration, assume authority if user_id contains community name
        return community_name.lower() in user_id.lower()


def main():
    """Example usage of the DSI Metadata Manager."""
    # Initialize manager
    manager = DSIMetadataManager()
    
    # Example sequence data
    sequence_data = "ATCGATCGATCGATCGATCG" * 100
    
    # Example collection info
    collection_info = {
        "sequence_type": "DNA",
        "collection_date": "2024-01-15",
        "collection_location": {"lat": -3.4653, "lon": -62.2159},  # Amazon region
        "tissue_type": "leaf"
    }
    
    # Example FAIR metadata
    fair_metadata = {
        "title": "Medicinal Plant Genome Sequence from Kayapó Territory",
        "description": "Complete genome sequence of traditional medicinal plant used by Kayapó community",
        "keywords": ["genomics", "traditional knowledge", "medicinal plants", "Amazon"],
        "creators": [
            {"name": "Dr. Maria Santos", "affiliation": "University of São Paulo"},
            {"name": "Kayapó Traditional Healer Council", "affiliation": "Kayapó Territory"}
        ],
        "license": "CC-BY-NC-SA",
        "usage_notes": "Use restricted to non-commercial research with benefit sharing",
        "citation": "Santos, M. et al. Medicinal plant genome from Kayapó territory. DSI Platform. 2024."
    }
    
    # Example CARE metadata
    care_metadata = {
        "community_benefits": [
            "Research collaboration opportunities",
            "Revenue sharing from commercial applications",
            "Traditional knowledge documentation"
        ],
        "benefit_sharing_terms": {
            "revenue_percentage": 0.02,
            "minimum_payment": 10000,
            "research_collaboration": True
        },
        "community_participation": True,
        "governance_structure": {
            "decision_body": "Kayapó Traditional Council",
            "consent_mechanism": "Community assembly",
            "review_frequency": "Annual"
        },
        "consent_requirements": {
            "community_name": "Kayapó Indigenous Territory",
            "consent_given": True,
            "consent_date": "2024-01-10",
            "consent_expires": "2029-01-10",
            "consent_scope": ["research", "commercial"],
            "restrictions": ["weapons development", "patenting of traditional knowledge"],
            "contact_person": "Elder João Kayapó, Traditional Council Chair"
        },
        "data_sovereignty_assertions": [
            "Community retains ownership of traditional knowledge",
            "Right to withdraw consent at any time",
            "Prior informed consent required for all uses"
        ],
        "ethical_review_status": "Approved by Indigenous Ethics Committee",
        "cultural_protocols": [
            "Respect for sacred knowledge boundaries",
            "Community attribution in all publications",
            "Seasonal restrictions on sample collection"
        ],
        "researcher_responsibilities": [
            "Annual progress reports to community",
            "Data sharing with community researchers",
            "Respect for traditional knowledge protocols"
        ],
        "ethical_considerations": [
            "Potential misuse of traditional knowledge",
            "Commercial exploitation concerns",
            "Cultural appropriation risks"
        ],
        "cultural_sensitivity": {
            "sacred_knowledge_excluded": True,
            "traditional_names_used": True,
            "community_review_required": True
        },
        "future_use_considerations": [
            "Climate change research applications",
            "Biodiversity conservation efforts",
            "Traditional medicine documentation"
        ]
    }
    
    print("Creating DSI metadata...")
    
    # Create metadata
    metadata = manager.create_dsi_metadata(
        sequence_id="KY_001_2024",
        sequence_data=sequence_data,
        organism="Uncaria tomentosa",
        collection_info=collection_info,
        fair_metadata=fair_metadata,
        care_metadata=care_metadata,
        created_by="dr.maria.santos@usp.br"
    )
    
    print(f"Created DSI: {metadata.dsi_id}")
    print(f"DOI: {metadata.doi}")
    print(f"IPLC Consent: {metadata.care.consent_requirements.consent_given}")
    
    # Test access permission check
    print("\nTesting access permissions...")
    
    access_result = manager.check_access_permissions(
        metadata.dsi_id,
        "researcher@university.edu",
        "research",
        "studying medicinal properties for cancer research"
    )
    
    print(f"Research access permitted: {access_result['permitted']}")
    print(f"Reason: {access_result['reason']}")
    
    # Test commercial access
    commercial_result = manager.check_access_permissions(
        metadata.dsi_id,
        "pharma@company.com",
        "commercial_use",
        "developing new pharmaceutical products"
    )
    
    print(f"Commercial access permitted: {commercial_result['permitted']}")
    print(f"Reason: {commercial_result['reason']}")
    
    # Generate JSON-LD
    print("\nGenerating JSON-LD...")
    jsonld_data = manager.generate_jsonld(metadata.dsi_id)
    print(f"JSON-LD type: {jsonld_data['@type']}")
    print(f"CARE consent: {jsonld_data['care:consentGiven']}")
    
    # Search metadata
    print("\nSearching metadata...")
    search_results = manager.search_dsi_metadata({
        "organism": "Uncaria",
        "keywords": ["medicinal"]
    })
    
    print(f"Found {len(search_results)} matching DSI assets")
    
    print("\nDSI Metadata Manager demo completed successfully!")


if __name__ == "__main__":
    main()
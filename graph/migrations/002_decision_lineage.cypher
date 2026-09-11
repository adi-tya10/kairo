// ============================================================================
// KAIRO: Neo4j Cypher Schema Migration (002)
// Multi-Tenant Indexes for Decision Lineage Traversals & Confidence Gating
// ============================================================================

CREATE INDEX decision_source_idx IF NOT EXISTS
FOR (d:Decision) ON (d.org_id, d.source);

CREATE INDEX decision_confidence_idx IF NOT EXISTS
FOR (d:Decision) ON (d.org_id, d.confidence);

CREATE INDEX decision_timestamp_idx IF NOT EXISTS
FOR (d:Decision) ON (d.org_id, d.timestamp);

// ============================================================================
// KAIRO: Neo4j Cypher Initial Constraints & Schema Migration (001)
// Temporal Knowledge Graph & Multi-Tenant Entity Relationships
// ============================================================================

// 1. Uniqueness Constraints (Multi-Tenant Scoped)
CREATE CONSTRAINT org_id_unique IF NOT EXISTS
FOR (o:Organization) REQUIRE o.id IS UNIQUE;

CREATE CONSTRAINT person_key_unique IF NOT EXISTS
FOR (p:Person) REQUIRE (p.org_id, p.id) IS UNIQUE;

CREATE CONSTRAINT task_key_unique IF NOT EXISTS
FOR (t:Task) REQUIRE (t.org_id, t.key) IS UNIQUE;

CREATE CONSTRAINT pr_key_unique IF NOT EXISTS
FOR (pr:PullRequest) REQUIRE (pr.org_id, pr.repo, pr.number) IS UNIQUE;

CREATE CONSTRAINT commit_sha_unique IF NOT EXISTS
FOR (c:Commit) REQUIRE (c.org_id, c.sha) IS UNIQUE;

CREATE CONSTRAINT decision_id_unique IF NOT EXISTS
FOR (d:Decision) REQUIRE (d.org_id, d.id) IS UNIQUE;

CREATE CONSTRAINT service_id_unique IF NOT EXISTS
FOR (s:Service) REQUIRE (s.org_id, s.name) IS UNIQUE;

CREATE CONSTRAINT file_path_unique IF NOT EXISTS
FOR (f:File) REQUIRE (f.org_id, f.repo, f.path) IS UNIQUE;

// 2. Indexes for fast 2-hop neighborhood traversals
CREATE INDEX person_email_idx IF NOT EXISTS
FOR (p:Person) ON (p.org_id, p.email);

CREATE INDEX task_status_idx IF NOT EXISTS
FOR (t:Task) ON (t.org_id, t.status);

CREATE INDEX pr_state_idx IF NOT EXISTS
FOR (pr:PullRequest) ON (pr.org_id, pr.state);

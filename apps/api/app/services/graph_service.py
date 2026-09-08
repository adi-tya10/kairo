"""
KAIRO Neo4j Temporal Knowledge Graph & Decision Lineage Service.
Tracks (Decision)-[:SUPERSEDES]->(OldChoice) and (Decision)-[:JUSTIFIES]->(Task).

All public methods require a live neo4j.Session — there is no silent fake fallback.
If the graph database is unavailable, callers receive a clear RuntimeError, not
synthetic data.
"""
from dataclasses import dataclass

from neo4j import Session as Neo4jSession


@dataclass
class DecisionNode:
    decision_id: str
    title: str
    rationale: str
    status: str
    supersedes: str | None = None


class GraphLineageService:
    """Temporal provenance and decision lineage graph manager."""

    @staticmethod
    def extract_decision_subgraph(
        organization_id: str,
        task_key: str,
        session: Neo4jSession,
    ) -> list[DecisionNode]:
        """
        Retrieves decision records justifying a work item task via a parameterized
        2-hop Cypher traversal scoped to the caller's organization.

        Args:
            organization_id: Tenant org ID — every query is scoped to this value.
            task_key: Jira/Linear task identifier (e.g. "BILL-204").
            session: A live neo4j.Session provided by the get_graph_db() dependency.

        Returns:
            List of DecisionNode records linked to the task. Empty list if none found.

        Raises:
            RuntimeError: If the Cypher query fails (e.g. connectivity lost mid-request).
        """
        # All node properties use org_id to match the schema in 001_initial_schema.cypher
        cypher_query = """
        MATCH (t:Task {key: $task_key, org_id: $org_id})<-[:JUSTIFIES]-(d:Decision)
        OPTIONAL MATCH (d)-[:SUPERSEDES]->(old:Decision)
        RETURN d.id AS decision_id,
               d.title AS title,
               d.rationale AS rationale,
               d.status AS status,
               old.title AS supersedes
        """
        try:
            result = session.run(cypher_query, task_key=task_key, org_id=organization_id)
            nodes: list[DecisionNode] = []
            for record in result:
                nodes.append(
                    DecisionNode(
                        decision_id=record["decision_id"],
                        title=record["title"],
                        rationale=record["rationale"],
                        status=record["status"],
                        supersedes=record.get("supersedes"),
                    )
                )
            return nodes
        except Exception as exc:
            raise RuntimeError(
                f"Neo4j query failed for task '{task_key}' in org '{organization_id}': {exc}"
            ) from exc

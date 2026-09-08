"""
KAIRO Cold-Start & Historical Git Ingestion Service.
Parses local git log history into normalized commit evidence and persists to
PostgreSQL (`events_raw`) and Neo4j temporal graph.
"""
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from apps.api.app.core.database import get_neo4j_driver, get_supabase_client
from apps.api.app.core.logging import get_logger
from packages.schemas.github_event import CommitInfo

logger = get_logger("kairo.services.cold_start")
ISSUE_KEY_PATTERN = re.compile(r"([A-Z]{2,10}-\d+)")


class ColdStartIngestionService:
    """Historical sync engine using native git CLI with PostgreSQL and Neo4j persistence."""

    @staticmethod
    def ingest_local_git_history(repo_path: str | Path, max_commits: int = 50) -> list[CommitInfo]:
        """
        Extracts recent git history using stdlib subprocess.
        """
        p = Path(repo_path)
        if not (p / ".git").exists():
            return []

        cmd = [
            "git",
            "-C",
            str(p),
            "log",
            f"-n{max_commits}",
            "--pretty=format:%H|%an|%ae|%at|%s",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning(f"Git CLI invocation failed: {exc}")
            return []

        commits: list[CommitInfo] = []
        for line in res.stdout.strip().splitlines():
            if not line or "|" not in line:
                continue
            parts = line.split("|", 4)
            if len(parts) < 5:
                continue
            sha, author_name, author_email, timestamp_str, message = parts
            try:
                committed_at = datetime.fromtimestamp(int(timestamp_str), tz=UTC)
            except ValueError:
                committed_at = datetime.now(UTC)

            commits.append(
                CommitInfo(
                    sha=sha,
                    author_name=author_name,
                    author_email=author_email,
                    message=message,
                    committed_at=committed_at,
                    files_changed=[],
                )
            )
        return commits

    @staticmethod
    def persist_historical_commits(
        organization_id: str,
        repo_name: str,
        commits: list[CommitInfo],
    ) -> int:
        """
        Persists historical commits into PostgreSQL `events_raw` and Neo4j graph nodes.
        Returns the count of successfully persisted records.
        """
        if not commits:
            return 0

        # 1. Persist to PostgreSQL events_raw
        try:
            db = get_supabase_client()
            for c in commits:
                record = {
                    "organization_id": organization_id,
                    "provider": "git_cli",
                    "event_type": "historical_commit",
                    "delivery_id": f"commit_{c.sha[:16]}",
                    "payload": {
                        "repo_name": repo_name,
                        "sha": c.sha,
                        "author_name": c.author_name,
                        "author_email": c.author_email,
                        "message": c.message,
                        "committed_at": c.committed_at.isoformat(),
                    },
                    "processed": True,
                }
                db.table("events_raw").upsert(record).execute()
            logger.info(f"Persisted {len(commits)} commits to PostgreSQL events_raw", extra={"organization_id": organization_id})
        except Exception as exc:
            logger.warning(f"Failed to persist historical commits to PostgreSQL (continuing): {exc}")

        # 2. Persist to Neo4j Graph
        try:
            driver = get_neo4j_driver()
            with driver.session() as session:
                for c in commits:
                    linked_keys = list(set(ISSUE_KEY_PATTERN.findall(c.message)))
                    session.run(
                        """
                        MERGE (r:Repository {name: $repo_name, org_id: $org_id})
                        MERGE (c:Commit {sha: $sha, org_id: $org_id})
                        ON CREATE SET c.message = $message, c.author = $author_name
                        MERGE (c)-[:COMMITTED_TO]->(r)
                        MERGE (d:Developer {email: $email, org_id: $org_id})
                        ON CREATE SET d.name = $author_name
                        MERGE (d)-[:AUTHORED]->(c)
                        """,
                        repo_name=repo_name,
                        org_id=organization_id,
                        sha=c.sha,
                        message=c.message,
                        author_name=c.author_name,
                        email=c.author_email,
                    )
                    for key in linked_keys:
                        session.run(
                            """
                            MERGE (t:Task {key: $task_key, org_id: $org_id})
                            WITH t
                            MATCH (c:Commit {sha: $sha, org_id: $org_id})
                            MERGE (c)-[:IMPLEMENTS]->(t)
                            """,
                            task_key=key,
                            org_id=organization_id,
                            sha=c.sha,
                        )
            logger.info(f"Synchronized {len(commits)} commits to Neo4j graph", extra={"organization_id": organization_id})
        except Exception as exc:
            logger.warning(f"Failed to synchronize historical commits to Neo4j (continuing): {exc}")

        return len(commits)

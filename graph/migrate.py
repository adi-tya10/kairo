"""
KAIRO Neo4j Migration Runner.
Applies parameterized Cypher schema migrations (constraints & indexes) against
the configured Neo4j AuraDB instance. Reads all credentials from get_settings()
— never uses hardcoded local defaults.

Usage:
    python graph/migrate.py --up
"""

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so apps.api imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from neo4j import GraphDatabase

from apps.api.app.core.config import get_settings


def run_migrations() -> None:
    settings = get_settings()

    if not settings.NEO4J_URI or not settings.NEO4J_USER or not settings.NEO4J_PASSWORD:
        print(
            "Error: NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must all be set in environment.",
            file=sys.stderr,
        )
        sys.exit(1)

    migration_file = Path(__file__).parent / "migrations" / "001_initial_schema.cypher"
    if not migration_file.exists():
        print(f"Error: Migration file {migration_file} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to Neo4j at {settings.NEO4J_URI} ...")
    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        with driver.session() as session:
            cypher_content = migration_file.read_text(encoding="utf-8")
            # Split statements by semicolon; skip comments and blank lines
            statements = [
                stmt.strip()
                for stmt in cypher_content.split(";")
                if stmt.strip() and not stmt.strip().startswith("//")
            ]

            for stmt in statements:
                preview = stmt[:80].replace("\n", " ")
                print(f"  Executing: {preview}...")
                session.run(stmt)

        print("Neo4j migrations applied successfully.")
        driver.close()
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="KAIRO Neo4j migration runner")
    parser.add_argument("--up", action="store_true", help="Apply all pending migrations")
    args = parser.parse_args()

    if args.up:
        run_migrations()
    else:
        print("Usage: python graph/migrate.py --up")
        sys.exit(1)

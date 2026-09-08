"""
KAIRO Cold-Start & Historical Git Ingestion Service.
Parses local git log history into normalized commit evidence.
"""
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from packages.schemas.github_event import CommitInfo

ISSUE_KEY_PATTERN = re.compile(r"([A-Z]+-\d+)")


class ColdStartIngestionService:
    """Historical sync engine using native git CLI."""

    @staticmethod
    def ingest_local_git_history(repo_path: str | Path, max_commits: int = 50) -> list[CommitInfo]:
        """
        Extracts recent git history using stdlib subprocess.
        # ponytail: native git log CLI over libgit2/pygit2 dependency.
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
        except (subprocess.SubprocessError, OSError):
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

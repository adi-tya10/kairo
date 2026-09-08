from pathlib import Path
from unittest.mock import MagicMock, patch

from apps.api.app.services.cold_start import ColdStartIngestionService


def test_cold_start_ingest_git_history_mocked() -> None:
    fake_log = "e91c2bf4a1288c9a1288c9a1288c9a1288c9a128|Rahul Sharma|rahul@snapmeet.com|1710000000|BILL-204: add retry\n"
    with patch("subprocess.run") as mock_run, patch("pathlib.Path.exists", return_value=True):
        mock_run.return_value = MagicMock(stdout=fake_log, returncode=0)
        commits = ColdStartIngestionService.ingest_local_git_history(Path("."))
        assert len(commits) == 1
        assert commits[0].sha == "e91c2bf4a1288c9a1288c9a1288c9a1288c9a128"
        assert commits[0].author_name == "Rahul Sharma"
        assert "BILL-204" in commits[0].message

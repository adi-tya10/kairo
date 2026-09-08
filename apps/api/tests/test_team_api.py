from typing import Any
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from apps.api.app.core.database import get_db
from apps.api.app.core.security import create_access_token
from apps.api.app.main import app

client = TestClient(app)


class MockTableQuery:
    def __init__(self, table_name: str, tables_data: dict[str, list[dict[str, Any]]]):
        self.table_name = table_name
        self.tables_data = tables_data
        self._filters: list[tuple[str, Any]] = []
        self._insert_data: Any = None
        self._is_delete: bool = False
        self._order_by: str | None = None
        self._desc: bool = False

    def select(self, *args: Any, **kwargs: Any) -> "MockTableQuery":
        return self

    def eq(self, col: str, val: Any) -> "MockTableQuery":
        self._filters.append((col, val))
        return self

    def order(self, col: str, desc: bool = False) -> "MockTableQuery":
        self._order_by = col
        self._desc = desc
        return self

    def insert(self, data: Any) -> "MockTableQuery":
        self._insert_data = data
        return self

    def upsert(self, data: Any, *args: Any, **kwargs: Any) -> "MockTableQuery":
        self._insert_data = data
        return self

    def delete(self) -> "MockTableQuery":
        self._is_delete = True
        return self

    def execute(self) -> MagicMock:
        table_rows = self.tables_data.setdefault(self.table_name, [])
        res = MagicMock()

        if self._insert_data is not None:
            items = self._insert_data if isinstance(self._insert_data, list) else [self._insert_data]
            created = []
            for it in items:
                row = dict(it)
                if "id" not in row:
                    row["id"] = f"{self.table_name[:2]}_{len(table_rows) + 1}"
                table_rows.append(row)
                created.append(row)
            res.data = created
            self._insert_data = None
            return res

        if self._is_delete:
            matched = []
            remaining = []
            for r in table_rows:
                match = any(r.get(col) == val for col, val in self._filters)
                if match:
                    matched.append(r)
                else:
                    remaining.append(r)
            self.tables_data[self.table_name] = remaining
            res.data = matched
            return res

        matched = []
        for r in table_rows:
            if all(r.get(col) == val for col, val in self._filters):
                matched.append(r)

        if self._order_by:
            order_field = self._order_by
            matched.sort(key=lambda x: str(x.get(order_field, "")), reverse=self._desc)

        res.data = matched
        return res


class MockSupabaseClient:
    def __init__(self, initial_data: dict[str, list[dict[str, Any]]] | None = None):
        self.tables_data: dict[str, list[dict[str, Any]]] = initial_data or {}

    def table(self, table_name: str) -> MockTableQuery:
        return MockTableQuery(table_name, self.tables_data)


def _get_seed_data() -> dict[str, list[dict[str, Any]]]:
    return {
        "organizations": [
            {"id": "snapmeet", "name": "Snapmeet Inc", "domain": "snapmeet.com"},
            {"id": "kairo-pvt-ldt", "name": "Kairo Ltd", "domain": "kairo.io"},
        ],
        "users": [
            {"id": "usr_snapmeet_admin", "organization_id": "snapmeet", "full_name": "Rahul Sharma", "email": "admin@snapmeet.com"},
            {"id": "usr_kairo_admin", "organization_id": "kairo-pvt-ldt", "full_name": "Lead Developer", "email": "admin@kairo.io"},
        ],
        "user_repo_permissions": [
            {"id": "p1", "organization_id": "snapmeet", "user_id": "usr_snapmeet_admin", "repo_id": "snapmeet/billing-service", "access_level": "admin"},
            {"id": "p2", "organization_id": "kairo-pvt-ldt", "user_id": "usr_kairo_admin", "repo_id": "kairo-pvt-ldt/primary-repo", "access_level": "admin"},
        ],
        "slack_channels": [
            {"id": "s_default", "organization_id": "snapmeet", "name": "#eng-continuity-alerts", "purpose": "Primary alert channel", "is_default": True},
        ],
        "work_items": [
            {"id": "w1", "organization_id": "snapmeet", "project_key": "BILL", "title": "BILL Service Pod", "source": "JIRA"},
        ],
        "handoff_packages": [
            {
                "id": "hf_89a1",
                "organization_id": "snapmeet",
                "task_key": "BILL-204",
                "from_user_id": "usr_snapmeet_admin",
                "to_user_id": "usr_snapmeet_admin",
                "status": "IN_PROGRESS",
                "briefing": {"repo_name": "snapmeet/billing-service", "citation_score": 1.0},
                "anomalies": [
                    {
                        "id": "anom_hw03_1",
                        "rule_id": "HW-03",
                        "severity": "HIGH",
                        "summary": "Declared vs Observed State Mismatch",
                        "task_key": "BILL-204",
                        "repo_name": "snapmeet/billing-service",
                        "detected_at": "2026-08-27T10:45:00Z",
                    }
                ],
                "created_at": "2026-08-27T14:30:00Z",
            }
        ],
    }


def test_team_continuity_spof_detection() -> None:
    from apps.api.app.engines.team_continuity import TeamContinuityEngine

    services = [
        {"repo_name": "snapmeet/billing-service", "primary_owner": "Rahul Sharma", "ownership_pct": 0.85, "active_maintainers": 1},
        {"repo_name": "snapmeet/auth-service", "primary_owner": "Alice Chen", "ownership_pct": 0.40, "active_maintainers": 3},
    ]
    risks = TeamContinuityEngine.evaluate_service_spof_risks("snapmeet", services)
    assert len(risks) == 2
    assert risks[0].risk_level == "CRITICAL"
    assert risks[1].risk_level == "LOW"


def test_api_team_continuity_endpoints() -> None:
    mock_db = MockSupabaseClient(_get_seed_data())
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        token = create_access_token({
            "sub": "usr_snapmeet_admin",
            "email": "admin@snapmeet.com",
            "org_id": "snapmeet",
            "allowed_repos": ["snapmeet/billing-service"],
            "is_org_admin": True,
        })
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Continuity Map
        res_map = client.get("/api/v1/team/continuity-map?organization_id=snapmeet", headers=headers)
        assert res_map.status_code == 200
        assert "service_risks" in res_map.json()
        assert len(res_map.json()["service_risks"]) == 1

        # 2. Anomalies Feed
        res_anom = client.get("/api/v1/team/anomalies-feed?organization_id=snapmeet", headers=headers)
        assert res_anom.status_code == 200
        assert "active_anomalies" in res_anom.json()
        assert len(res_anom.json()["active_anomalies"]) == 1

        # 3. Handoff History
        res_hf = client.get("/api/v1/team/handoff-history?organization_id=snapmeet", headers=headers)
        assert res_hf.status_code == 200
        assert "history" in res_hf.json()
        assert len(res_hf.json()["history"]) == 1
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_api_team_continuity_dynamic_new_tenant() -> None:
    mock_db = MockSupabaseClient(_get_seed_data())
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        token = create_access_token({
            "sub": "usr_kairo_admin",
            "email": "admin@kairo.io",
            "org_id": "kairo-pvt-ldt",
            "allowed_repos": ["kairo-pvt-ldt/primary-repo"],
            "is_org_admin": True,
        })
        headers = {"Authorization": f"Bearer {token}"}

        res_map = client.get("/api/v1/team/continuity-map?organization_id=kairo-pvt-ldt", headers=headers)
        assert res_map.status_code == 200
        data = res_map.json()
        assert data["organization_id"] == "kairo-pvt-ldt"
        assert len(data["service_risks"]) == 1
        assert data["service_risks"][0]["repo_name"] == "kairo-pvt-ldt/primary-repo"

        res_anom = client.get("/api/v1/team/anomalies-feed?organization_id=kairo-pvt-ldt", headers=headers)
        assert res_anom.status_code == 200
        assert len(res_anom.json()["active_anomalies"]) == 0

        res_hf = client.get("/api/v1/team/handoff-history?organization_id=kairo-pvt-ldt", headers=headers)
        assert res_hf.status_code == 200
        assert len(res_hf.json()["history"]) == 0
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_api_team_integrations_crud_flow() -> None:
    mock_db = MockSupabaseClient(_get_seed_data())
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        token = create_access_token({
            "sub": "usr_snapmeet_admin",
            "email": "admin@snapmeet.com",
            "org_id": "snapmeet",
            "allowed_repos": ["snapmeet/billing-service"],
            "is_org_admin": True,
        })
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Get Integrations
        res_get = client.get("/api/v1/team/snapmeet/integrations", headers=headers)
        assert res_get.status_code == 200
        data = res_get.json()
        assert "repositories" in data
        assert "slack_channels" in data
        assert "projects" in data

        # 2. Add and Delete Repo
        res_add_repo = client.post(
            "/api/v1/team/snapmeet/repos",
            headers=headers,
            json={"name": "snapmeet/auth-service", "branch": "main", "provider": "github"},
        )
        assert res_add_repo.status_code == 201
        repo_id = res_add_repo.json()["repository"]["id"]

        res_del_repo = client.delete(f"/api/v1/team/snapmeet/repos/{repo_id}", headers=headers)
        assert res_del_repo.status_code == 200

        # 3. Add and Delete Channel
        res_add_chan = client.post(
            "/api/v1/team/snapmeet/channels",
            headers=headers,
            json={"name": "#devops-oncall", "purpose": "On-call alerts"},
        )
        assert res_add_chan.status_code == 201
        chan_id = res_add_chan.json()["channel"]["id"]

        res_del_chan = client.delete(f"/api/v1/team/snapmeet/channels/{chan_id}", headers=headers)
        assert res_del_chan.status_code == 200

        # 4. Add and Delete Project
        res_add_proj = client.post(
            "/api/v1/team/snapmeet/projects",
            headers=headers,
            json={"key": "AUTH", "name": "Auth Pod", "tool": "jira"},
        )
        assert res_add_proj.status_code == 201
        proj_id = res_add_proj.json()["project"]["id"]

        res_del_proj = client.delete(f"/api/v1/team/snapmeet/projects/{proj_id}", headers=headers)
        assert res_del_proj.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)

def test_api_team_repos_fallback_delete_and_user_creation() -> None:
    mock_db = MockSupabaseClient(_get_seed_data())
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        # Token with a user ID not in users table yet
        token = create_access_token({
            "sub": "usr_brand_new",
            "email": "newbie@snapmeet.com",
            "org_id": "snapmeet",
            "allowed_repos": ["snapmeet/new-repo"],
            "is_org_admin": True,
        })
        headers = {"Authorization": f"Bearer {token}"}

        # Adding repo triggers user auto-creation upsert
        res_add = client.post(
            "/api/v1/team/snapmeet/repos",
            headers=headers,
            json={"name": "new-service", "branch": "dev", "provider": "github"},
        )
        assert res_add.status_code == 201

        # Delete using repo name (fallback when id is not UUID)
        res_del = client.delete("/api/v1/team/snapmeet/repos/new-service", headers=headers)
        assert res_del.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)

def test_api_team_projects_fallback_delete() -> None:
    mock_db = MockSupabaseClient(_get_seed_data())
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        token = create_access_token({
            "sub": "usr_snapmeet_admin",
            "email": "admin@snapmeet.com",
            "org_id": "snapmeet",
            "allowed_repos": ["snapmeet/billing-service"],
            "is_org_admin": True,
        })
        headers = {"Authorization": f"Bearer {token}"}

        # Add project
        res_add = client.post(
            "/api/v1/team/snapmeet/projects",
            headers=headers,
            json={"key": "CORE", "name": "Core Pod", "tool": "linear"},
        )
        assert res_add.status_code == 201

        # Delete using project_key instead of row UUID (fallback branch)
        res_del = client.delete("/api/v1/team/snapmeet/projects/CORE", headers=headers)
        assert res_del.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_api_team_auth_rejection() -> None:
    # Missing or invalid token should return 401
    bad_headers = {"Authorization": "Bearer invalid_token_123"}
    res = client.get("/api/v1/team/continuity-map?organization_id=snapmeet", headers=bad_headers)
    assert res.status_code == 401

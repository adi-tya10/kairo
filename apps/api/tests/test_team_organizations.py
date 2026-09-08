from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from apps.api.app.core.database import get_db
from apps.api.app.core.security import create_access_token
from apps.api.app.main import app


class MockTableQuery:
    def __init__(self, storage: dict[str, dict]):
        self.storage = storage
        self._selected_id = None
        self._insert_data = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, column: str, value: str):
        if column == "id":
            self._selected_id = value
        return self

    def insert(self, data: dict):
        self._insert_data = data
        return self

    def execute(self):
        mock_res = MagicMock()
        if self._insert_data is not None:
            org_id = self._insert_data["id"]
            self.storage[org_id] = dict(self._insert_data)
            self.storage[org_id]["created_at"] = "2026-09-05T12:00:00Z"
            self.storage[org_id]["updated_at"] = "2026-09-05T12:00:00Z"
            mock_res.data = [self.storage[org_id]]
            self._insert_data = None
            return mock_res

        if self._selected_id:
            if self._selected_id in self.storage:
                mock_res.data = [self.storage[self._selected_id]]
            else:
                mock_res.data = []
        else:
            mock_res.data = list(self.storage.values())
        return mock_res



class MockSupabaseDB:
    def __init__(self, persistent_storage: dict[str, dict]):
        self.persistent_storage = persistent_storage

    def table(self, table_name: str):
        if table_name == "organizations":
            return MockTableQuery(self.persistent_storage)
        raise ValueError(f"Unknown table: {table_name}")


def test_organization_crud_with_simulated_server_restart():
    """
    Verifies that an organization created via the API persists to the database,
    and after simulating a server restart (re-initializing the app client),
    fetching the organization still returns the persisted data.
    """
    # 1. Shared persistent database storage (representing Postgres database)
    postgres_persistent_storage: dict[str, dict] = {}
    mock_db = MockSupabaseDB(postgres_persistent_storage)

    app.dependency_overrides[get_db] = lambda: mock_db

    token = create_access_token({
        "sub": "usr_superadmin",
        "email": "superadmin@kairo.dev",
        "org_id": "master_org",
        "is_org_admin": True,
    })
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Create organization via server instance 1
    client1 = TestClient(app)
    create_payload = {
        "id": "org_acme_corp",
        "name": "Acme Corporation",
        "domain": "acme.com",
    }
    create_res = client1.post("/api/v1/team/organizations", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["id"] == "org_acme_corp"
    assert data["name"] == "Acme Corporation"
    assert data["domain"] == "acme.com"

    # Step 2: Simulate complete server restart (destroy client1, recreate fresh client2)
    del client1
    client2 = TestClient(app)

    # Step 3: Fetch organization from server instance 2 — must still exist in database
    get_res = client2.get("/api/v1/team/organizations/org_acme_corp", headers=headers)
    assert get_res.status_code == 200
    persisted = get_res.json()
    assert persisted["id"] == "org_acme_corp"
    assert persisted["name"] == "Acme Corporation"
    assert persisted["domain"] == "acme.com"

    # Step 4: Verify list endpoint also returns the persisted organization
    list_res = client2.get("/api/v1/team/organizations", headers=headers)
    assert list_res.status_code == 200
    all_orgs = list_res.json()
    assert any(o["id"] == "org_acme_corp" for o in all_orgs)

    # Clean up override
    app.dependency_overrides.clear()


def test_organization_error_cases():
    postgres_persistent_storage: dict[str, dict] = {}
    mock_db = MockSupabaseDB(postgres_persistent_storage)
    app.dependency_overrides[get_db] = lambda: mock_db

    token = create_access_token({
        "sub": "usr_superadmin",
        "email": "superadmin@kairo.dev",
        "org_id": "master_org",
        "is_org_admin": True,
    })
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(app)

    # 1. 404 on non-existent organization
    res_404 = client.get("/api/v1/team/organizations/non_existent_org", headers=headers)
    assert res_404.status_code == 404

    # 2. 409 on duplicate organization creation
    client.post(
        "/api/v1/team/organizations",
        json={"id": "org_dup", "name": "Dup Corp", "domain": "dup.com"},
        headers=headers,
    )
    res_409 = client.post(
        "/api/v1/team/organizations",
        json={"id": "org_dup", "name": "Dup Corp", "domain": "dup.com"},
        headers=headers,
    )
    assert res_409.status_code == 409

    # 3. 400 on empty fields
    res_400 = client.post(
        "/api/v1/team/organizations",
        json={"id": "", "name": "Empty", "domain": "empty.com"},
        headers=headers,
    )
    assert res_400.status_code == 400

    # 4. 401 on invalid token
    res_401 = client.get("/api/v1/team/organizations", headers={"Authorization": "Bearer invalid_token"})
    assert res_401.status_code == 401

    app.dependency_overrides.clear()

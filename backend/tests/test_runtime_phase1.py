"""Runtime regression coverage for auth, tickets, comments, and tenant isolation."""
import os
import uuid
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


def login(email):
    response = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": "Synapse123!"})
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == email
    assert data["token"]
    return data["token"]


def test_public_contract_and_unauthorized():
    assert requests.get(f"{BASE_URL}/api/health").json()["status"] == "ok"
    assert requests.get(f"{BASE_URL}/openapi.json").status_code == 200
    assert requests.get(f"{BASE_URL}/api/dashboard").status_code == 401
    assert requests.get(f"{BASE_URL}/api/tickets").status_code == 401


def test_admin_dashboard_ticket_comment_flow():
    token = login("admin@acme.test")
    headers = {"Authorization": f"Bearer {token}"}
    dashboard = requests.get(f"{BASE_URL}/api/dashboard", headers=headers)
    assert dashboard.status_code == 200 and "team_workload" in dashboard.json()
    tickets = requests.get(f"{BASE_URL}/api/tickets", headers=headers)
    assert tickets.status_code == 200 and tickets.json()
    ticket = tickets.json()[0]
    detail = requests.get(f"{BASE_URL}/api/tickets/{ticket['id']}", headers=headers)
    assert detail.status_code == 200 and detail.json()["id"] == ticket["id"]
    marker = f"TEST_runtime_{uuid.uuid4().hex}"
    comment = requests.post(f"{BASE_URL}/api/tickets/{ticket['id']}/comments", headers=headers, json={"content": marker})
    assert comment.status_code == 200 and comment.json()["content"] == marker


def test_cross_tenant_ticket_is_hidden():
    admin = login("admin@acme.test")
    registration = requests.post(f"{BASE_URL}/api/auth/register", json={"email": f"{uuid.uuid4().hex}@test.invalid", "password": "Synapse123!", "name": "TEST Tenant", "organization_name": "TEST Isolated"})
    assert registration.status_code == 200
    other_headers = {"Authorization": f"Bearer {registration.json()['token']}"}
    ticket = requests.get(f"{BASE_URL}/api/tickets", headers={"Authorization": f"Bearer {admin}"}).json()[0]
    response = requests.get(f"{BASE_URL}/api/tickets/{ticket['id']}", headers=other_headers)
    assert response.status_code == 404
import os
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
PASSWORD = "Synapse123!"


def login(email):
    response = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["email"] == email
    return data["user"], {"Authorization": f"Bearer {data['token']}"}


def test_seeded_roles_and_platform_access():
    superadmin, super_headers = login("agent@acme.test")
    admin, admin_headers = login("admin@acme.test")
    employee, employee_headers = login("requester@acme.test")
    assert superadmin["role"] == "superadmin"
    assert admin["role"] == "admin"
    assert employee["role"] == "requester"
    assert requests.get(f"{BASE_URL}/api/platform/organizations", headers=super_headers).status_code == 200
    assert requests.get(f"{BASE_URL}/api/platform/organizations", headers=admin_headers).status_code == 403
    assert requests.get(f"{BASE_URL}/api/platform/organizations", headers=employee_headers).status_code == 403


def test_employee_restricted_endpoints_and_my_tickets():
    _, headers = login("requester@acme.test")
    assert requests.get(f"{BASE_URL}/api/my/tickets", headers=headers).status_code == 200
    for endpoint in ("/api/users", "/api/audit"):
        assert requests.get(f"{BASE_URL}{endpoint}", headers=headers).status_code == 403


def test_admin_scoped_endpoints_and_superadmin_global_data():
    _, admin_headers = login("admin@acme.test")
    _, super_headers = login("agent@acme.test")
    for endpoint in ("/api/dashboard", "/api/tickets", "/api/users", "/api/audit"):
        assert requests.get(f"{BASE_URL}{endpoint}", headers=admin_headers).status_code == 200
        assert requests.get(f"{BASE_URL}{endpoint}", headers=super_headers).status_code == 200
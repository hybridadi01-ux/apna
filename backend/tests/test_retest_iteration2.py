"""Live regression coverage for requester authorization and disabled integrations."""
import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://tenant-first-tickets.preview.emergentagent.com").rstrip("/")
PASSWORD = "Synapse123!"


def auth(email):
    response = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PASSWORD}, timeout=20)
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_requester_owns_creation_and_cannot_access_other_ticket():
    requester = auth("requester@acme.test")
    created = requests.post(f"{BASE_URL}/api/tickets", headers=requester, json={"title": "TEST requester request", "description": "Regression", "requester": "Jamie Patel", "requester_email": "requester@acme.test"}, timeout=20)
    assert created.status_code == 200
    own_id = created.json()["id"]
    own = requests.get(f"{BASE_URL}/api/tickets/{own_id}", headers=requester, timeout=20)
    assert own.status_code == 200 and own.json()["requester_email"] == "requester@acme.test"
    admin_tickets = requests.get(f"{BASE_URL}/api/tickets", headers=auth("admin@acme.test"), timeout=20).json()
    other_id = next(t["id"] for t in admin_tickets if t["requester_email"] != "requester@acme.test") if any(t["requester_email"] != "requester@acme.test" for t in admin_tickets) else None
    if other_id:
        assert requests.get(f"{BASE_URL}/api/tickets/{other_id}", headers=requester, timeout=20).status_code == 404
        assert requests.patch(f"{BASE_URL}/api/tickets/{other_id}", headers=requester, json={"status": "Closed"}, timeout=20).status_code == 404
        assert requests.post(f"{BASE_URL}/api/tickets/{other_id}/comments", headers=requester, json={"content": "TEST unauthorized"}, timeout=20).status_code == 404


def test_admin_agent_and_disabled_contracts():
    admin = auth("admin@acme.test")
    agent = auth("agent@acme.test")
    admin_tickets = requests.get(f"{BASE_URL}/api/tickets", headers=admin, timeout=20)
    assert admin_tickets.status_code == 200 and admin_tickets.json()
    assert requests.get(f"{BASE_URL}/api/tickets", headers=agent, timeout=20).status_code == 200
    ticket_id = admin_tickets.json()[0]["id"]
    card = requests.get(f"{BASE_URL}/api/integrations/teams/card/{ticket_id}", headers=agent, timeout=20).json()
    assert card["mode"] == "not_configured"
    assert [a["title"] for a in card["card"]["actions"]] == ["Acknowledge", "Working", "Waiting", "Resolved", "Add Update"]
    ai = requests.post(f"{BASE_URL}/api/ai/analyze/{ticket_id}", headers=admin, timeout=20).json()
    assert ai["enabled"] is False
    assert requests.post(f"{BASE_URL}/api/ai/actions", headers=admin, json={"action": "classify"}, timeout=20).json()["enabled"] is False
    assert requests.get(f"{BASE_URL}/api/voice/status", timeout=20).json()["enabled"] is False
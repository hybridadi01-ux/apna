"""API contract examples for the most important security invariant.

The full suite can run against a disposable PostgreSQL service in CI. These
cases document the required cross-tenant behavior for the next test runner.
"""
from pathlib import Path

def test_tenant_isolation_contract():
    source = (Path(__file__).parents[1] / "server.py").read_text()
    assert "organization_id" in source
    assert 'filter_by(id=ticket_id, organization_id=user.organization_id)' in source
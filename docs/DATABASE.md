# Database

The SQLAlchemy schema includes organizations, users, teams, tickets, comments, attachments, and audit logs. PostgreSQL is the Docker Compose default. The local preview uses SQLite only when `DATABASE_URL` is absent, keeping the product easy to inspect without requiring infrastructure.

Indexes are applied to organization identifiers, ticket numbers, status, priority, and team-oriented fields. The production deployment should add Alembic migrations before the first schema change; the current bootstrap creates the initial schema on startup for the Phase 1 single-node installation.
# SynapseDesk

SynapseDesk is a lightweight, self-hosted, multi-tenant ticket operations platform. It uses a modular FastAPI backend, PostgreSQL in Docker, React, and Nginx without queues, caches, search clusters, or paid runtime services.

## Run locally

Run `docker compose up --build`, then open `http://localhost`. API documentation is available at `http://localhost/api/docs`.

Development seed access: `admin@acme.test`, `agent@acme.test`, and `requester@acme.test`, all using `Synapse123!`.

The first phase includes JWT authentication, organization-scoped tickets, comments, attachments, SLA visibility, audit records, dashboard metrics, REST/OpenAPI, responsive navigation, and the AI-disabled configuration seam. See `docs/` for architecture, security, API, and deployment notes.

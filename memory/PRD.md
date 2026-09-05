# SynapseDesk Phase 1 PRD

## Original problem statement
Build a new lightweight self-hosted multi-tenant ticket management platform as the production-ready foundation for an AI-first ticket operations product, optimized for a single low-resource VM and without mandatory AI, Teams, Slack, or voice services in Phase 1.

## Architecture decisions
- Modular monolith with FastAPI, React, PostgreSQL, and Nginx in Docker Compose.
- Organization-scoped records and backend predicates provide tenant isolation.
- JWT + bcrypt authentication with centralized role checks.
- Local filesystem attachment storage with a configurable path.
- Provider-neutral AI configuration defaults to `none`.

## Personas and requirements
Organization admins manage users and workspace settings; team managers coordinate queues; agents resolve tickets; employees/requesters submit and follow requests. Core needs are authentication, tenant isolation, RBAC, tickets, comments, attachments, SLA visibility, audit history, dashboard, API docs, seed data, tests, and self-hosted deployment.

## Implemented
2026-03-06: Added the tenant-aware FastAPI API, SQLAlchemy schema, seed organization/users/tickets, JWT auth, ticket CRUD, comments, attachments, dashboard, audit records, React workspace, responsive design system, Docker Compose PostgreSQL/Nginx stack, docs, and test contract scaffold.
2026-03-06: Added the requester-only employee portal, requester-owned ticket authorization, confirm/reopen service endpoints, Teams Adaptive Card contract, disabled AI/action contracts, voice status architecture, and fixed public OpenAPI routing. Iteration 2 verification passed backend and frontend flows at 100%.

## Prioritized backlog
P0: production migrations, refresh rotation, password reset, authorized attachment downloads, complete API integration tests.
P1: configure Azure Bot credentials for real Teams delivery/actions; configure OpenAI credentials for classification and audited tools; configure calling credentials for real voice actions.
P2: configurable SLA policies, granular permission records, notifications/email, workflows, user/team management, SSO, business hours, Slack.
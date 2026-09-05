# Architecture

SynapseDesk is a modular monolith. The API owns authentication, tenant scoping, authorization, ticket workflows, SLA fields, audit events, and local attachment metadata. The React application is a thin client and never filters tenant data as a security mechanism.

Every tenant-owned table has `organization_id`; every query in the API scopes through the authenticated user's organization. Future domain modules can be extracted behind the current REST/event boundaries.

The event vocabulary is represented by audit actions such as `ticket.created`, `ticket.updated`, `comment.added`, and `attachment.uploaded`. A future notification worker can subscribe to these actions without changing ticket commands. The AI seam is configuration-only in Phase 1 and should call controlled application services rather than database access.
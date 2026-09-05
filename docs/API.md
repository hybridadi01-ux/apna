# API

FastAPI publishes OpenAPI at `/api/openapi.json` and Swagger UI at `/api/docs`.

Core routes: `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me`, `GET /api/dashboard`, `GET/POST /api/tickets`, `GET/PATCH /api/tickets/{id}`, `POST /api/tickets/{id}/comments`, `POST /api/tickets/{id}/attachments`, `GET /api/teams`, `GET /api/users`, `GET /api/audit`, and `GET /api/health`.

Send `Authorization: Bearer <token>` after login. All ticket, comment, attachment, team, user, and audit responses are scoped to the token's organization.
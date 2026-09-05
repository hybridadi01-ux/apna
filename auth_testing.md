# Authentication testing notes

Use the seed users in `/app/memory/test_credentials.md`. Login returns a bearer token; pass it to `/api/auth/me`, `/api/tickets`, and `/api/dashboard`. The API must return 401 without a token and must never return another organization's ticket when a valid user changes the ticket id.
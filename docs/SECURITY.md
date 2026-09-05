# Security

Passwords are bcrypt-hashed and never returned. JWT access tokens carry a short-lived signed identity and protected routes verify that the user remains active. Tenant isolation is enforced in backend query predicates, not by client-side filtering. Role checks are centralized in the `require(...)` dependency.

Before production: replace `JWT_SECRET`, set explicit `CORS_ORIGINS`, run behind HTTPS, configure a non-public attachment path, add rate limiting at Nginx, and move schema bootstrapping to reviewed migrations. Password reset, SSO/OAuth, email delivery, and refresh-token rotation are planned architecture items rather than falsely presented Phase 1 features.
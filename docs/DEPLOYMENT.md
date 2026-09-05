# Deployment on a small Oracle VM

Install Docker and Docker Compose on the VM, copy the repository, set a long random `JWT_SECRET` in the Compose environment, then run:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f backend
```

Point a domain at the VM and terminate TLS at Nginx before exposing the service publicly. Use a regular database backup of the `postgres_data` volume and a separate backup of `uploads_data`. Keep one backend worker on a 1 vCPU / 1 GB host; the Compose configuration deliberately does so. PostgreSQL, FastAPI, and the static frontend are the only runtime services required.
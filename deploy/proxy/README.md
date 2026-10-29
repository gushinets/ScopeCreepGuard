# Deployment routing

Expose the frontend app on port 3000 through the deployment reverse proxy.
Nginx serves the static React frontend and forwards /api paths to internal http://backend:8000;
FastAPI remains internal unless a deployment deliberately adds a compatible
reverse-proxy route. Keep same-origin cookies, allowed origins and shared auth
secret unchanged. Development also publishes backend port 8000.

Use `deploy/docker-compose.dokploy.yml` as the platform Compose Path, preserving
the existing project name and environment. The local canonical entry point is
`deploy/compose.yaml` (pass the root `.env` explicitly). PostgreSQL health gates
the one-shot `migrate` service; guarded locked Alembic must complete successfully
before API or workers start. API/workers never migrate at startup; backend
readiness gates frontend. Keep local Mailpit outside public proxy routes.
Production uses one API worker/replica for the existing in-process generation
limiter. Publish matching image pairs; rollback images without downgrading schema
or enabling retired Drizzle migration tooling.

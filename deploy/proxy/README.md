# Deployment routing

Expose the frontend app on port 3000 through the deployment reverse proxy.
Next.js forwards existing /api paths once to internal http://backend:8000;
FastAPI remains internal unless a deployment deliberately adds a compatible
reverse-proxy route. Keep same-origin cookies, allowed origins and shared auth
secret unchanged. Development also publishes backend port 8000.

PostgreSQL health gates the API entrypoint; guarded locked Alembic completes
before API starts; backend readiness gates frontend. Only API containers migrate.
Production uses one API worker/replica for the existing in-process generation
limiter. Publish matching image pairs; rollback images without downgrading schema
or enabling retired Drizzle migration tooling.

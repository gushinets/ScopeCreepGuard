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

### Trusted client sources

Supported production path: browser -> Dokploy/Traefik -> app Nginx -> internal
backend. Development also allows browser -> app or direct backend access. No
backend ports/exposure are added by client-source propagation.

`SCOPE_GUARD_TRUSTED_PROXY_HOSTS` is a JSON list of up to eight explicit proxy
service DNS names or IP literals. Compose defaults to `["app"]`; standalone API
defaults to `[]`. The backend compares its actual socket peer with freshly resolved
addresses of those names (one-second DNS deadline, no stale trust cache). This
supports container replacement without assuming Docker addresses are stable.
Use only names controlled by deployment DNS on an isolated application network;
never point this at a public/uncontrolled DNS name or grant untrusted containers
the `app` alias. Resolution failure falls back to the socket peer. Uvicorn remains
`--no-proxy-headers`; API access logs are disabled to avoid logging client addresses.

Nginx always overwrites `X-Scope-Guard-Client-IP` with `$remote_addr`; callers'
versions are discarded. The backend accepts exactly one syntactically valid IPv4
or IPv6 value only from a trusted immediate peer. Missing, duplicate, scoped or
malformed values fall back to the peer, as do all untrusted direct requests.
`X-Forwarded-For` is never interpreted by the backend. Confirmation and recovery
share this resolver; separate global limits still apply.

For an edge proxy in front of Nginx, set `SCOPE_GUARD_EDGE_PROXY_CIDRS` to a
space-separated list of the actual trusted edge network CIDRs. Empty (default)
means Nginx trusts no upstream forwarding headers. Configure a dedicated,
operator-controlled Traefik network/subnet and use that subnet here; do not assume
its individual container IP stays constant. Never use a shared network containing
untrusted workloads, `0.0.0.0/0`, `::/0`, or wildcard trust. The edge must overwrite
caller forwarding information and append the actual connection address; Nginx
real-IP recursion selects the last untrusted hop. Do not add public client ranges
to the trusted list. Production operators must supply this setting to obtain
independent browser quotas behind Traefik; without it all clients of that edge
safely share its quota. Direct development clients continue using their actual
peer/NAT address. NAT itself cannot distinguish users sharing one public address.

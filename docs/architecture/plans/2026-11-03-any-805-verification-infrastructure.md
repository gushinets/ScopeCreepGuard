# ANY-805 verification infrastructure repair

Base: aa622ac2a76dd894ec1895cafd890f61850715f4. Existing branch:
codex/any-805-frontend-security, primary checkout; no new worktree.
Preserve the diagnostic report and all unrelated untracked reports.

## Scope and order

1. Reproduce the tariff-test failure caused by inherited settings and LiteLLM's
   automatic dotenv loading. Add a subprocess regression using an external cwd.
2. Add a single backend pytest launcher that uses the workspace interpreter,
   backend cwd, isolated application environment and an owned writable temp path.
   Wire CI and document the same invocation for local diagnostic agents.
3. Give the fixed-source test storage Dockerfile dedicated, locked module/build
   caches. Keep the exact upstream release and resource limits. Do not delete or
   modify shared caches and do not change production storage or Compose topology.
4. Verify the launcher regression, backend unit/API and targeted SQL/SDK tests,
   fresh storage build and its private read/write behavior. Re-run the canonical
   disposable lifecycle harness if prerequisites are available. No paid LLM calls.
5. Record actual results and limitations. No existing DB/volume resets, shared
   cache pruning, unrelated-service shutdown or changes to application behavior.

## Evidence

The diagnostic report records EOF syntax errors in shared /go/pkg/mod contents;
LiteLLM __init__ calls python-dotenv in DEV mode. Scratch evidence belongs in
ignored output/infra-repair-20261103. Record final commands/results below.

## Implemented and verified

- `scripts/test_backend.py` runs the current interpreter's pytest from backend,
  removes inherited application/DB/provider settings, disables python-dotenv
  before SDK import and owns a unique writable basetemp. Explicit test arguments
  are forwarded. CI and README now use this same entry point.
- A subprocess regression launches from another directory with poisoned rate
  settings and a synthetic dotenv file. It failed before the entry point existed
  and passes with it. No original test assertions or application settings changed.
- The MinIO Dockerfile retains the exact upstream source release and Go resource
  bounds, but uses fixture-specific locked cache IDs. This bypasses the damaged
  generic cache without deleting or repairing shared cache contents. The original
  cause of those damaged files is not established; concurrency protection reduces
  one risk and is not a claim to repair disk corruption globally.
- Backend unit/API: 939 passed (113.90s), through the new launcher while the real
  root .env remains present. SQL/workflow matrix: 9 passed (104.42s) using the new
  launcher, owned PostgreSQL and controlled SDK HTTP responses. No paid calls.
- CI infrastructure unittest suite: 15 passed, including the new subprocess
  regression. Ruff check/format and diff whitespace checks pass for new Python.
- Fresh fixed-source storage build passed; cold Go step 362.9s. Repeated build
  passed using the cache. Initial runtime image manifest digest:
  sha256:505e28ccd4943637f9157e79f18295abdd8b1b07a3ab727ad08bab4edcc1eab9;
  runtime config digest: sha256:20927ff55ddb0e4469968c5a1935c9d15fdbb044785b797d7b32d47a443b65a6.
  The canonical release fixture tag was updated to this freshly built image;
  original image identity is retained in ignored previous-storage-image.txt.
  go install embeds DEVELOPMENT.GOGET in --version; source pin/build log, not
  that display string, identifies the fixed release.
- Lifecycle verification uses official runtime images from the preceding
  diagnostic head aa622ac (application code and locked dependencies unchanged):
  API e56545e38164fbf65fd4015291824354d37fd830a0150dbd254f139a6c14b293;
  worker 9eaf456fdf1a3a15fb81f8fa660a1ac2018f257a97c978ad4e37dce4437bb010;
  frontend f1c9cc05373df2bba1ac8d444dec5c8f43c2d4753e921a04128f171210377558.
  Current tracked differences affect test/CI infrastructure and documentation only.
  The canonical verify_docker_startup.py lifecycle completed with exit 0 on
  Compose 5.6.0 using the freshly built storage fixture. It verified complete
  stack readiness and component dependency closures, Mailpit capture and email
  confirmation, onboarding, project/draft save/read through Nginx, no-op and
  concurrent migrations, rollback after process termination, maintenance updates
  preserving users, and safe handling of failed migrations/partial releases.
  Its owned containers were cleaned up; existing application DBs/volumes and
  unrelated services were not modified. No new live-model quality evaluation or
  full browser/export acceptance is claimed by this infrastructure verification.

Evidence: storage-build.log, storage-rebuild.log, backend-tests.log,
llm-sql-tests.log, ci-tests.log and compose-lifecycle.log under the ignored folder.

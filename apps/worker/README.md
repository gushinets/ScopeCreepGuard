# Future worker contract

There is no running worker, queue, polling loop or jobs table in this refactor.
A future worker is a composition root that invokes the same backend services as
the API. It must not call repositories, sessions or ORM models directly and must
not run Alembic migrations.

Long-running LLM, PDF and delivery work may eventually use a transactional outbox
and a worker process. That design must preserve service inputs/results, owner
checks, explicit Unit of Work boundaries, draft idempotency and immutable history.
Provider and document adapters remain in backend integrations; orchestration
remains in services. Any queue/outbox schema or delivery provider needs a separate
approved implementation plan. The current generation limiter still requires one
production API worker/replica.

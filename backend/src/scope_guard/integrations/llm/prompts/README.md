Legacy v1 assets preserve the pre-cutover prompt contract and compatibility tests.
`workflow_v2.py` explicitly composes native structured stage prompts, reusing the
established tone skills and commercial rules without extracting sections by marker.
NativeOutput owns the response shape; reply skills apply only to their text field.

New durable steps and analysis runs record `workflow-v3`: the compositor projects
each stage's required frozen inputs instead of serializing the entire Draft.
Full snapshots remain authoritative for local validation and persistence. Provider
input limits are unchanged; there is no truncation. The worker refuses an
older pending operation's v1/v2 steps with `workflowVersionUnavailable`, before any
new provider call or accepted-stage reuse. Do not rewrite versions/checkpoints or
reset its budgets. Completed v1/v2 results remain readable; an explicit new command
may use v3 within existing idempotency rules. Drain old work before coordinated
activation if it must complete under its original worker. No migration is needed.

# Safe main integration

Base: codex/design-onboarding 22a13be; existing local checkout, no worktree.
User authorized merging GitHub work and synchronizing local main.
Scope: PRs 37/39; preserve local .taste-skill outside publication.

1. Verified both PR heads have successful Application checks; merged PR39.
2. Found unresolved PR37 review about wrong-project fallback after archive load failure.
3. Added a regression test: 11 passed / new test failed before fix.
4. Preserve explicit project selection and expose archive-load failure; rerun focused tests and typecheck in Docker.
5. Publish fix, merge via protected PR workflow, fast-forward local main to origin/main.

No database changes or paid model calls. GitHub required checks remain mandatory.

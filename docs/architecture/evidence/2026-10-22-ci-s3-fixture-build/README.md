# Test S3 image build and diagnostics

The supplied CI run passed 943 tests and failed while building the owned MinIO test server, before any S3 assertions. The helper captured Docker stdout/stderr but raised a generic `CalledProcessError`, so the original CI log does not establish the exact underlying build failure.

Local reproduction of the previous unbounded build ended with a Docker RPC EOF. This is evidence of an interrupted build, not proof that the original CI failure was OOM. Official prebuilt images of the same release were unavailable to the local registry probes, so the existing pinned-source approach was retained.

## Changes

- Keep Go 1.24.2 and MinIO release `RELEASE.2025-04-22T22-12-26Z` unchanged.
- Bound source-build parallelism to one package and two Go execution threads, with a 512 MiB Go soft memory target. Cache downloaded modules and compiler outputs through BuildKit mounts rather than storing them in the image layer.
- Use plain Docker build progress. On any failed fixture command, report its exit code, stdout and stderr directly in pytest instead of hiding the useful failure details.
- Add focused tests for failed-command diagnostics and successful stdout handling. Production S3 code, conditional-write assertions, restart persistence assertions and owned-container cleanup are unchanged.

## Verification

- Cold Docker source build passed: compile/download step 339.4 seconds, image exported successfully.
- The actual `test_conditional_s3_upload_and_storage_restart` and two diagnostic regressions passed together: **3 tests in 9.43 seconds**. The integration test built the image through Docker, created an owned local MinIO server, wrote an object, verified overwrite rejection, restarted the server, and read the original bytes.
- Diagnostic tests also passed separately inside Docker: **2 tests**.
- Targeted Ruff check and format check passed; git diff check passed.

The end-to-end S3 test was driven by the workspace Windows Python 3.12.10 environment (pytest 9.1.1, boto3 1.43.112) against Docker's Linux MinIO server. The Linux Docker environment separately ran the diagnostic regressions. No configured application bucket or real provider credentials were used. The entire 946-test suite was not rerun for this follow-up; a fresh CI run remains authoritative for the complete job.

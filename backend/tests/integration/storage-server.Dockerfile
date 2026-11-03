# Test-only S3 server built from a fixed upstream source release. Not a production dependency.
FROM golang:1.24.2 AS builder
# Keep this fixed-source fixture out of unrelated Go builds' mutable caches.
# Locked sharing prevents simultaneous builders from observing incomplete writes.
RUN --mount=type=cache,id=scg-minio-20250422-go1242-mod-v1,target=/go/pkg/mod,sharing=locked \
    --mount=type=cache,id=scg-minio-20250422-go1242-build-v1,target=/root/.cache/go-build,sharing=locked \
    GOMAXPROCS=2 GOMEMLIMIT=512MiB \
    go install -p=1 github.com/minio/minio@RELEASE.2025-04-22T22-12-26Z

FROM python:3.12-slim
COPY --from=builder /go/bin/minio /usr/local/bin/minio
ENTRYPOINT ["minio"]

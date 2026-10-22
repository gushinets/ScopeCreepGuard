# Test-only S3 server built from a fixed upstream source release. Not a production dependency.
FROM golang:1.24.2 AS builder
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    GOMAXPROCS=2 GOMEMLIMIT=512MiB \
    go install -p=1 github.com/minio/minio@RELEASE.2025-04-22T22-12-26Z

FROM python:3.12-slim
COPY --from=builder /go/bin/minio /usr/local/bin/minio
ENTRYPOINT ["minio"]

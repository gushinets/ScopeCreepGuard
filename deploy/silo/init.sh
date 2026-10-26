#!/bin/sh
set -eu

# The bucket name is also embedded in the IAM JSON policy below.
case "$SCOPE_GUARD_EXPORT_BUCKET" in
  ''|*[!a-z0-9.-]*) echo 'Invalid export bucket name' >&2; exit 1 ;;
esac

mcli alias set exports http://silo:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
mcli mb --ignore-existing "exports/$SCOPE_GUARD_EXPORT_BUCKET"
mcli anonymous set none "exports/$SCOPE_GUARD_EXPORT_BUCKET"
mcli admin user add exports "$SCOPE_GUARD_EXPORT_ACCESS_KEY" "$SCOPE_GUARD_EXPORT_SECRET_KEY" >/dev/null
cat > /tmp/export-policy.json <<EOF
{"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Action":["s3:ListBucket"],"Resource":["arn:aws:s3:::$SCOPE_GUARD_EXPORT_BUCKET"],"Condition":{"StringLike":{"s3:prefix":["exports/scg-*"]}}},
  {"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":["arn:aws:s3:::$SCOPE_GUARD_EXPORT_BUCKET/exports/scg-*"]}
]}
EOF
mcli admin policy create exports scg-exports /tmp/export-policy.json
mcli admin policy attach exports scg-exports --user "$SCOPE_GUARD_EXPORT_ACCESS_KEY" >/dev/null

#!/bin/sh
set -eu

# Compose's one-shot migrate service owns all schema changes.
exec "$@"

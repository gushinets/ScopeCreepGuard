#!/bin/sh
set -eu
# Space-separated, explicitly trusted edge CIDRs. Empty means direct Nginx access.
# Reject configuration injection and universal trust before Nginx validates CIDRs.
: > /tmp/scope-guard-real-ip.conf
for network in ${SCOPE_GUARD_EDGE_PROXY_CIDRS:-}; do
    case "$network" in
        *[!0-9a-fA-F.:/]*|*/0*|0.0.0.0|::)
            echo 'Invalid trusted edge proxy network' >&2; exit 1 ;;
    esac
    printf 'set_real_ip_from %s;\n' "$network" >> /tmp/scope-guard-real-ip.conf
done
printf 'real_ip_header X-Forwarded-For;\nreal_ip_recursive on;\n' >> /tmp/scope-guard-real-ip.conf

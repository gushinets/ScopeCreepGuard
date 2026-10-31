"""Resolve rate-limit sources without delegating trust to forwarding headers."""

import asyncio
import ipaddress
import socket

from fastapi import Request


def address(value: str) -> str:
    if "%" in value:
        raise ValueError("scoped address")
    parsed = ipaddress.ip_address(value)
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped:
        return str(parsed.ipv4_mapped)
    return str(parsed)


async def client_source(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        peer = address(peer)
    except ValueError:
        return peer
    hosts = request.app.state.settings.trusted_proxy_hosts
    if not hosts:
        return peer

    async def resolve(host):
        try:
            return {address(host)}
        except ValueError:
            try:
                records = await asyncio.get_running_loop().getaddrinfo(
                    host, None, type=socket.SOCK_STREAM
                )
                return {address(record[4][0]) for record in records}
            except (OSError, ValueError):
                return set()

    try:
        async with asyncio.timeout(1):
            trusted = await asyncio.gather(*(resolve(host) for host in hosts))
    except TimeoutError:
        return peer
    if not any(peer in addresses for addresses in trusted):
        return peer
    values = request.headers.getlist("x-scope-guard-client-ip")
    if len(values) != 1:
        return peer
    try:
        return address(values[0])
    except ValueError:
        return peer

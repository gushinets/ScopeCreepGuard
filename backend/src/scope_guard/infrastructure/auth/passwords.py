"""bcryptjs-compatible UTF-8, 72-byte truncation and nonblocking cost-12 hashing."""

import asyncio

import bcrypt


def password_bytes(password: str) -> bytes:
    # bcryptjs encodes unmatched UTF-16 surrogates literally, unlike TextEncoder.
    value = password.encode("utf-16-le", errors="surrogatepass").decode(
        "utf-16-le", errors="surrogatepass"
    )
    return value.encode("utf-8", errors="surrogatepass")[:72]


class Passwords:
    async def hash(self, password: str) -> str:
        return (
            await asyncio.to_thread(
                bcrypt.hashpw, password_bytes(password), bcrypt.gensalt(rounds=12)
            )
        ).decode("ascii")

    async def verify(self, password: str, hashed: str) -> bool:
        try:
            return await asyncio.to_thread(
                bcrypt.checkpw, password_bytes(password), hashed.encode("ascii")
            )
        except (ValueError, UnicodeError):
            return False

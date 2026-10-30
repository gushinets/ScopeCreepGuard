"""Run inside the checks image on an isolated Mailpit Compose network."""

import asyncio
import json
from urllib.request import urlopen

from scope_guard.core.config import Settings
from scope_guard.integrations.email.smtp import SMTPSender, mime_message
from scope_guard.services.email.service import EmailService


def read(path):
    with urlopen("http://mailpit:8025/api/v1/" + path, timeout=5) as response:
        return json.load(response)


async def main():
    settings = Settings(_env_file=None)
    service = EmailService(SMTPSender(settings))
    for kind in ("confirmation", "password_recovery"):
        for locale in ("ru", "en"):
            recipient = f"{kind}-{locale}@example.test"
            url = f"http://localhost:3000/action?synthetic={kind}-{locale}&x=1"
            message = service.prepare(kind, recipient, url, locale)
            await service.send(message)
            listing = read("messages")["messages"]
            entry = next(m for m in listing if m["To"][0]["Address"] == recipient)
            actual = read("message/" + entry["ID"])
            assert actual["From"]["Address"] == settings.smtp_sender_address
            assert actual["To"][0]["Address"] == recipient
            assert actual["Subject"] == message.subject
            assert actual["Text"].replace("\r\n", "\n").strip() == message.text
            assert actual["HTML"].replace("\r\n", "\n").strip() == message.html
            assert url in actual["Text"]
            assert ("24 часа" if locale == "ru" else "24 hours") in actual["Text"]
            assert str(mime_message(message, settings)["Message-ID"]).strip("<>") == actual[
                "MessageID"
            ].strip("<>")
    print("PASS: four real SMTP messages verified through Mailpit API")


if __name__ == "__main__":
    asyncio.run(main())

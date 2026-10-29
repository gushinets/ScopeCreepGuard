"""Exercise local SMTP capture using an isolated standard-library client.

Default: create a UUID Compose project, then stop it without removing volumes.
Use --project to inspect Mailpit in an already running isolated full stack.
"""

import argparse
import json
import os
import subprocess
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project")
    parser.add_argument("--client-image", default="python:3.12-alpine")
    args = parser.parse_args()
    project = args.project or "scg-mailpit-test-" + uuid4().hex
    environment = dict(os.environ, MAILPIT_UI_PORT="0", COMPOSE_DISABLE_ENV_FILE="1")
    base = ["docker", "compose", "-p", project, "-f", str(ROOT / "deploy/compose.mailpit.yaml")]

    def run(command, **kwargs):
        result = subprocess.run(
            command, cwd=ROOT, env=environment, text=True, capture_output=True, **kwargs
        )
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout.strip()

    def compose(*command):
        return run([*base, *command])

    try:
        if not args.project:
            compose("up", "-d", "--wait", "--wait-timeout", "90")
        identifier = compose("ps", "-q", "mailpit")
        container = json.loads(run(["docker", "inspect", identifier]))[0]
        assert container["State"]["Health"]["Status"] == "healthy"
        bindings = container["HostConfig"]["PortBindings"]
        assert set(bindings) == {"8025/tcp"}, bindings
        assert all(item["HostIp"] == "127.0.0.1" for item in bindings["8025/tcp"])
        settings = dict(item.split("=", 1) for item in container["Config"]["Env"])
        assert not any(
            key.startswith(("MP_SMTP_RELAY", "MP_SMTP_FORWARD", "MP_SMTP_AUTH")) for key in settings
        )
        assert settings["MP_DATABASE"] == "/data/mailpit.db"
        assert settings["MP_MAX_MESSAGES"] == "500" and settings["MP_MAX_AGE"] == "7d"
        network = project + "_default"
        marker = "ANY-778-" + uuid4().hex
        client = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            network,
            "--entrypoint",
            "python",
            args.client_image,
            "-",
        ]
        source = """
import json, smtplib, time, urllib.request
from email.message import EmailMessage
marker = MARKER
def get(path):
    return json.load(urllib.request.urlopen('http://mailpit:8025/api/v1/' + path, timeout=5))
if SEND:
    message = EmailMessage()
    message['From'] = 'no-reply-scopecreepguard@mail.com'
    message['To'] = 'any778@example.test'
    message['Subject'] = marker
    message.set_content('Technical SMTP text ' + marker)
    message.add_alternative('<p>Technical SMTP HTML ' + marker + '</p>', subtype='html')
    with smtplib.SMTP('mailpit', 1025, timeout=10) as smtp:
        assert smtp.send_message(message) == {}
for attempt in range(50):
    messages = get('messages')['messages']
    matches = [m for m in messages if m['Subject'] == marker]
    if matches:
        break
    time.sleep(.2)
assert len(matches) == 1
message = get('message/' + matches[0]['ID'])
assert message['To'][0]['Address'] == 'any778@example.test'
assert message['From']['Address'] == 'no-reply-scopecreepguard@mail.com'
assert message['Subject'] == marker
assert 'Technical SMTP text ' + marker in message['Text']
assert '<p>Technical SMTP HTML ' + marker + '</p>' in message['HTML']
print(json.dumps({'id': message['ID'], 'subject': marker, 'content_verified': True}))
"""
        first = run(client, input=source.replace("MARKER", repr(marker)).replace("SEND", "True"))
        compose("restart", "mailpit")
        # --wait can be used without rebuilding or replacing the container.
        compose("up", "-d", "--wait", "--wait-timeout", "90")
        second = run(client, input=source.replace("MARKER", repr(marker)).replace("SEND", "False"))
        assert json.loads(first) == json.loads(second)
        print(
            json.dumps(
                {
                    "project": project,
                    "smtp_and_restart": json.loads(second),
                    "loopback_ui_only": True,
                    "no_relay": True,
                    "image_id": container["Image"],
                },
                indent=2,
            )
        )
    finally:
        if not args.project:
            compose("down")
            print("Retained disposable volume: " + project + "_scope_creep_guard_mailpit")


if __name__ == "__main__":
    main()

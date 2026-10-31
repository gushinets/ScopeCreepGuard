"""Owned password-recovery contour. Never starts llm-worker or deletes volumes.

Run from repository root with the workspace Python. `start` persists synthetic
configuration in output/any782. `check` exercises HTTP/Mailpit; `stop` stops only
this contour. Existing application settings are not read.
"""

import argparse
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output/any782"
STATE = OUTPUT / "contour.json"


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def compose(state, *args):
    assert state["project"].startswith("scg-any782-")
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("SCOPE_GUARD_", "COMPOSE_", "POSTGRES_"))
        and key not in ("AUTH_SECRET", "OPENAI_API_KEY", "DATABASE_URL")
    }
    environment["COMPOSE_DISABLE_ENV_FILE"] = "1"
    command = [
        "docker",
        "compose",
        "--env-file",
        str(OUTPUT / "synthetic.env"),
        "-p",
        state["project"],
        "-f",
        "deploy/compose.frontend.yaml",
        "-f",
        "deploy/compose.email-worker.yaml",
        "-f",
        "deploy/compose.mailpit.yaml",
        *args,
    ]
    result = subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True)
    if result.returncode:
        # Only this harness's generated synthetic environment is loaded.
        raise RuntimeError("Synthetic Compose failed:\n" + result.stdout + result.stderr)
    return result.stdout


def start():
    if STATE.exists():
        raise RuntimeError("Existing contour record: use check/stop; never overwrite ownership")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    state = {
        "project": "scg-any782-" + uuid4().hex[:10],
        "frontend": free_port(),
        "backend": free_port(),
        "mailpit": free_port(),
    }
    public = f"http://127.0.0.1:{state['frontend']}"
    empty = OUTPUT / "empty.env"
    empty.write_text("")
    settings = {
        "COMPOSE_PROJECT_NAME": state["project"],
        "AUTH_SECRET": "synthetic-any782-secret-32-characters",
        "OPENAI_API_KEY": "synthetic-no-llm-calls",
        "SCOPE_GUARD_OPENAI_MODEL": "gpt-6-luna",
        "SCOPE_GUARD_LLM_INPUT_RATE_BOUND": "0.000001",
        "SCOPE_GUARD_LLM_OUTPUT_RATE_BOUND": "0.000005",
        "SCOPE_GUARD_EXPORT_BUCKET": "recovery-private-test",
        "SCOPE_GUARD_EXPORT_ENDPOINT": "http://storage:9000",
        "SCOPE_GUARD_EXPORT_ACCESS_KEY": "synthetic",
        "SCOPE_GUARD_EXPORT_SECRET_KEY": "synthetic-storage-secret",
        "SCOPE_GUARD_API_IMAGE": "scope-guard-api:any782",
        "SCOPE_GUARD_FRONTEND_IMAGE": "scope-guard-frontend:any782",
        "FRONTEND_PORT": f"127.0.0.1:{state['frontend']}",
        "BACKEND_PORT": f"127.0.0.1:{state['backend']}",
        "MAILPIT_UI_PORT": str(state["mailpit"]),
        "POSTGRES_PORT": "127.0.0.1:0",
        "SCOPE_GUARD_PUBLIC_APP_URL": public,
        "SCOPE_GUARD_ALLOWED_ORIGINS": json.dumps([public]),
        **{
            key: str(empty).replace("\\", "/")
            for key in (
                "SCOPE_GUARD_LOCAL_ENV_FILE",
                "SCOPE_GUARD_LOCAL_OVERRIDE_ENV_FILE",
                "SCOPE_GUARD_BACKEND_ENV_FILE",
            )
        },
    }
    (OUTPUT / "synthetic.env").write_text(
        "\n".join(f"{key}='{value}'" for key, value in settings.items()) + "\n"
    )
    STATE.write_text(json.dumps(state, indent=2))
    print(compose(state, "up", "-d", "--no-build", "--wait", "postgres"))
    storage = state["project"] + "-storage"
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            storage,
            "--network",
            state["project"] + "_default",
            "--network-alias",
            "storage",
            "-e",
            "MINIO_ROOT_USER=synthetic",
            "-e",
            "MINIO_ROOT_PASSWORD=synthetic-storage-secret",
            "scope-guard-s3-test:release20250422",
            "server",
            "/data",
        ],
        check=True,
        capture_output=True,
    )
    print(compose(state, "up", "-d", "--no-build", "--wait"))
    private_storage(state)
    print(json.dumps(state))


def message_for(state, recipient, subject):
    origin = f"http://127.0.0.1:{state['mailpit']}"
    with httpx.Client(base_url=origin, trust_env=False) as client:
        for _ in range(40):
            for item in client.get("/api/v1/messages").json().get("messages", []):
                if item["Subject"] == subject and any(
                    address["Address"] == recipient for address in item["To"]
                ):
                    return client.get("/api/v1/message/" + item["ID"]).json()
            time.sleep(0.25)
    raise AssertionError("Expected Mailpit message not found")


def check(state):
    private_storage(state)
    origin = f"http://127.0.0.1:{state['frontend']}"
    sensitive = ["original-password", "replacement-password"]
    for language, subject in (("ru", "Восстановление пароля"), ("en", "Reset your password")):
        email = f"recovery-{language}-{uuid4().hex[:8]}@example.test"
        with httpx.Client(base_url=origin, trust_env=False) as client:
            registered = client.post(
                "/api/auth/register",
                json={"email": email, "password": "original-password", "locale": language},
            )
            assert registered.status_code == 201
            owner = registered.json()["user"]["id"]
            old_session = client.cookies.get("scg_session")
            response = client.post(
                "/api/auth/password/request", json={"email": email, "locale": language}
            )
            assert response.status_code == 202 and response.json() == {"ok": True}
            message = message_for(state, email, subject)
            link = next(line for line in message["Text"].splitlines() if line.startswith("http"))
            page = client.get(link)
            assert page.status_code == 200 and "no-store" in page.headers["cache-control"]
            token = parse_qs(urlsplit(link).fragment)["token"][0]
            sensitive.append(token)
            result = client.post(
                "/api/auth/password/reset",
                json={
                    "userId": owner,
                    "token": token,
                    "password": "replacement-password",
                    "locale": language,
                },
            )
            assert result.status_code == 200 and "set-cookie" not in result.headers
            assert (
                client.get(
                    "/api/auth/me", headers={"Cookie": "scg_session=" + old_session}
                ).status_code
                == 401
            )
            assert (
                client.post(
                    "/api/auth/login", json={"email": email, "password": "original-password"}
                ).status_code
                == 401
            )
            signed_in = client.post(
                "/api/auth/login", json={"email": email, "password": "replacement-password"}
            )
            assert signed_in.status_code == 200 and signed_in.json()["user"]["id"] == owner
            notification_subject = (
                "Пароль изменён" if language == "ru" else "Your password was changed"
            )
            message_for(state, email, notification_subject)
    logs = compose(state, "logs", "--no-color", "backend", "app", "email-worker")
    assert all(value not in logs for value in sensitive), "Sensitive recovery data in service logs"
    print(
        "PASS: RU/EN request, Mailpit, non-consuming GET, reset, "
        "session revocation, old/new login, notification"
    )


def check_client_sources(state):
    """Actual Nginx -> Uvicorn -> PostgreSQL, using distinct existing containers."""
    program = """
import json, urllib.request, urllib.error, uuid
statuses=[]
for i in range(11):
 request=urllib.request.Request(ORIGIN+'/api/auth/password/request',
  data=json.dumps({'email':str(uuid.uuid4())+'@example.test'}).encode(),
  headers={'Content-Type':'application/json',
   'X-Scope-Guard-Client-IP':'198.51.100.'+str(i+1),
   'X-Forwarded-For':'203.0.113.'+str(i+1)})
 try:
  with urllib.request.urlopen(request, timeout=10) as response:
   statuses.append(response.status)
 except urllib.error.HTTPError as error:
  statuses.append(error.code)
assert statuses == [202]*10+[429], statuses
print('PASS independent source quota and forged-header rejection')
"""
    # Both calls use app Nginx, but have distinct real network peers. The second
    # must retain its complete quota after the first has exhausted its own.
    for service in ("backend", "email-worker"):
        print(
            compose(
                state, "exec", "-T", service, "python", "-c", "ORIGIN='http://app:3000'\n" + program
            ).strip()
        )
    # Direct backend access remains usable and cannot trust caller forwarding.
    print(
        compose(
            state,
            "exec",
            "-T",
            "backend",
            "python",
            "-c",
            "ORIGIN='http://127.0.0.1:8000'\n" + program,
        ).strip()
    )


def private_storage(state):
    compose(
        state,
        "exec",
        "-T",
        "backend",
        "python",
        "-c",
        """
import os,boto3
from botocore.exceptions import ClientError
client=boto3.client('s3',endpoint_url=os.environ['SCOPE_GUARD_EXPORT_ENDPOINT'],
 aws_access_key_id=os.environ['SCOPE_GUARD_EXPORT_ACCESS_KEY'],
 aws_secret_access_key=os.environ['SCOPE_GUARD_EXPORT_SECRET_KEY'])
bucket=os.environ['SCOPE_GUARD_EXPORT_BUCKET']
if bucket not in [item['Name'] for item in client.list_buckets()['Buckets']]:
 client.create_bucket(Bucket=bucket)
client.head_bucket(Bucket=bucket)
try:
 client.get_bucket_policy(Bucket=bucket)
 raise AssertionError('Synthetic bucket must have no public policy')
except ClientError as error:
 assert error.response['Error']['Code']=='NoSuchBucketPolicy'
""",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "check", "diagnose", "stop"))
    args = parser.parse_args()
    if args.action == "start":
        start()
    else:
        state = json.loads(STATE.read_text())
        if args.action == "check":
            check(state)
            check_client_sources(state)
        elif args.action == "diagnose":
            print(compose(state, "ps", "--all"))
            print(compose(state, "logs", "--no-color", "--tail", "100"))
        else:
            print(compose(state, "stop"))
            subprocess.run(
                ["docker", "stop", state["project"] + "-storage"], check=True, capture_output=True
            )

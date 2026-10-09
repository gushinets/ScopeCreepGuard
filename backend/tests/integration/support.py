"""Owned ephemeral infrastructure and journal replay, never production configuration."""

import hashlib
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[3]


def migration_digest(content: bytes) -> str:
    """Source provenance only; never substitutes for Drizzle's raw-byte ledger hash."""
    return hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()


def docker(*args):
    return subprocess.run(
        ["docker", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


class DisposablePostgres:
    def __enter__(self):
        self.name = "scg-any639-test-" + uuid4().hex
        self.token = uuid4().hex
        self.container_id = docker(
            "run",
            "--rm",
            "-d",
            "--name",
            self.name,
            "--label",
            "scope-guard.disposable=" + self.token,
            "-e",
            "POSTGRES_USER=scg_test",
            "-e",
            "POSTGRES_PASSWORD=" + self.token,
            "-e",
            "POSTGRES_DB=scg_test_admin",
            "-p",
            "127.0.0.1::5432",
            "postgres:17-alpine",
        )
        try:
            port = docker("port", self.container_id, "5432/tcp").rsplit(":", 1)[1]
            self.admin_url = f"postgresql://scg_test:{self.token}@127.0.0.1:{port}/scg_test_admin"
            for _ in range(60):
                try:
                    with psycopg.connect(self.admin_url, connect_timeout=1):
                        return self
                except psycopg.OperationalError:
                    time.sleep(0.5)
            raise RuntimeError("Disposable PostgreSQL did not become ready")
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        # The immutable container ID and ownership label prevent unrelated cleanup.
        label = docker(
            "inspect",
            "--format",
            '{{index .Config.Labels "scope-guard.disposable"}}',
            self.container_id,
        )
        if label != self.token:
            raise RuntimeError("Disposable container ownership mismatch")
        docker("rm", "-f", self.container_id)

    @contextmanager
    def database(self):
        name = "scg_test_" + uuid4().hex
        with psycopg.connect(self.admin_url, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        url = self.admin_url.rsplit("/", 1)[0] + "/" + name
        try:
            yield url
        finally:
            with psycopg.connect(self.admin_url, autocommit=True) as connection:
                connection.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
                )


def replay_drizzle(url):
    """Invoke the installed production migrator against the owned disposable target."""
    script = """
      import postgres from 'postgres';
      import {drizzle} from 'drizzle-orm/postgres-js';
      import {migrate} from 'drizzle-orm/postgres-js/migrator';
      const sql = postgres(process.argv[1], {max: 1, onnotice: () => {}});
      try { await migrate(drizzle(sql), {migrationsFolder: 'drizzle'}); }
      finally { await sql.end(); }
    """
    subprocess.run(
        ["node", "--input-type=module", "--eval", script, url],
        cwd=ROOT / "frontend",
        check=True,
        capture_output=True,
        text=True,
    )


def rows(connection):
    result = {}
    for table in ("users", "projects", "history_entries", "drafts", "evaluation_cases"):
        result[table] = (
            connection.exec_driver_sql(
                f"SELECT row_to_json(t) FROM (SELECT * FROM {table} ORDER BY id) t"
            )
            .scalars()
            .all()
        )
    return result

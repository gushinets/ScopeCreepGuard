"""Timing calibration exclusively on verify_password_recovery's synthetic contour."""

import json
import random
import statistics
import time
from uuid import uuid4

import httpx
from verify_password_recovery import OUTPUT, STATE, compose


def main():
    state = json.loads(STATE.read_text())
    seed = uuid4().hex[:8]

    def sql(statement):
        return compose(
            state,
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "scopeguard",
            "-d",
            "scope_creep_guard",
            "-c",
            statement,
        )

    sql(
        "INSERT INTO users(email,password_hash) SELECT 'bench-"
        + seed
        + "-'||n||'@example.test','synthetic-unused' FROM generate_series(0,999) n"
    )
    result = {}
    rng = random.Random(782)

    def percentile(values, fraction):
        return sorted(values)[int((len(values) - 1) * fraction)]

    for phase in ("worker-stopped", "worker-running"):
        compose(state, "stop" if phase == "worker-stopped" else "start", "email-worker")
        samples = {"known": [], "unknown": []}
        order = [(kind, index) for index in range(500) for kind in samples]
        rng.shuffle(order)
        with httpx.Client(
            base_url=f"http://127.0.0.1:{state['frontend']}", trust_env=False
        ) as client:
            for position, (kind, index) in enumerate(order):
                if position % 8 == 0:
                    # Expire windows between synthetic batches, outside measured requests.
                    # All samples remain ordinary durable 202 admissions with unique addresses.
                    sql(
                        "UPDATE recovery_limits SET "
                        "expires_at=clock_timestamp()-interval '1 second'"
                    )
                number = index + (500 if phase == "worker-running" else 0)
                email = (
                    ("bench-" if kind == "known" else "missing-") + seed + f"-{number}@example.test"
                )
                started = time.perf_counter()
                response = client.post(
                    "/api/auth/password/request", json={"email": email, "locale": "en"}
                )
                elapsed = (time.perf_counter() - started) * 1000
                assert response.status_code == 202 and response.json() == {"ok": True}
                samples[kind].append(elapsed)
        result[phase] = {
            kind: {
                "n": len(values),
                "p50_ms": statistics.median(values),
                "p95_ms": percentile(values, 0.95),
                "p99_ms": percentile(values, 0.99),
            }
            for kind, values in samples.items()
        }
        differences = []
        for _ in range(1000):
            differences.append(
                statistics.median(rng.choices(samples["known"], k=500))
                - statistics.median(rng.choices(samples["unknown"], k=500))
            )
        result[phase]["median_difference_95pct_ms"] = [
            percentile(differences, 0.025),
            percentile(differences, 0.975),
        ]
    (OUTPUT / "timing.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

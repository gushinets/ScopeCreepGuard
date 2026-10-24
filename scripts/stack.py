"""Fixed Compose interface; also used by the Windows convenience wrapper."""

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = {
    "front": "frontend",
    "back": "backend",
    "postgres": "postgres",
    "llm_worker": "llm-worker",
    "export_worker": "export-worker",
}
SERVICES = {
    "front": "app",
    "back": "backend",
    "postgres": "postgres",
    "llm_worker": "llm-worker",
    "export_worker": "export-worker",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "update", "logs", "status", "down"])
    parser.add_argument("component", nargs="?", choices=list(COMPONENTS))
    parser.add_argument("--project")
    parser.add_argument("--env-file")
    parser.add_argument("--production", action="store_true")
    parser.add_argument(
        "--pull", action="store_true", help="Use published release images instead of building"
    )
    args = parser.parse_args()
    if args.component and (args.production or args.action not in {"up", "logs"}):
        parser.error("component selection is supported only for local up or logs")
    filename = "docker-compose.dokploy.yml" if args.production else "compose.yaml"
    if args.action == "up" and args.component:
        filename = f"compose.{COMPONENTS[args.component]}.yaml"
    base = ["docker", "compose", "-f", str(ROOT / filename)]
    if args.project:
        base += ["-p", args.project]
    if args.env_file:
        base += ["--env-file", str(Path(args.env_file).resolve())]

    def compose(*command):
        subprocess.run([*base, *command], cwd=ROOT, check=True)

    try:
        compose("config", "--quiet")
        if args.action == "update":
            # Images are prepared before stopping the old release. No volume removal.
            compose("pull" if args.pull else "build")
            compose("stop", "app", "backend", "llm-worker", "export-worker")
            compose("up", "-d", "--no-build", "--wait", "postgres")
            compose(
                "up",
                "--no-deps",
                "--no-build",
                "--force-recreate",
                "--abort-on-container-exit",
                "--exit-code-from",
                "migrate",
                "migrate",
            )
            compose(
                "up",
                "-d",
                "--no-deps",
                "--no-build",
                "--force-recreate",
                "--wait",
                "backend",
                "llm-worker",
                "export-worker",
            )
            compose("up", "-d", "--no-deps", "--no-build", "--force-recreate", "--wait", "app")
        elif args.action == "up":
            if args.pull:
                compose("pull")
            compose("up", "-d", "--no-build" if args.pull else "--build", "--wait")
        elif args.action == "logs":
            compose("logs", "--follow", *([SERVICES[args.component]] if args.component else []))
        elif args.action == "status":
            compose("ps", "--all")
        else:
            compose("down")
    except subprocess.CalledProcessError as error:
        return error.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

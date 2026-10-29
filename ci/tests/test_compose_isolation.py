"""The config matrix must not fall back to developer secrets through include."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "startup", ROOT / "backend/scripts/verify_docker_startup.py"
)
startup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(startup)


class ComposeIsolationTests(unittest.TestCase):
    def test_fixture_excludes_developer_env_and_unrelated_reports(self):
        with tempfile.TemporaryDirectory(prefix="scg-copy-") as directory:
            source = Path(directory) / "source"
            target = Path(directory) / "target"
            startup.copy_deployment_fixture(ROOT, source)
            for name in (
                ".env",
                ".env.local",
                "backend/.env",
                "deploy/compose/.env",
                "docs/private-report.md",
            ):
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("SYNTHETIC_POISON=must-not-copy")
            startup.copy_deployment_fixture(source, target)
            for name in (
                ".env",
                ".env.local",
                "backend/.env",
                "deploy/compose/.env",
                "docs/private-report.md",
            ):
                self.assertFalse((target / name).exists(), name)
            self.assertEqual(
                (target / "deploy/.env").read_bytes(), (source / "deploy/.env").read_bytes()
            )
            for definition in (source / "deploy/compose").glob("*.yaml"):
                self.assertEqual(
                    definition.read_bytes(),
                    (target / "deploy/compose" / definition.name).read_bytes(),
                )


if __name__ == "__main__":
    unittest.main()

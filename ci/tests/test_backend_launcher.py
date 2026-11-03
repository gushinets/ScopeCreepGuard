"""Exercise the public test entry point with hostile local configuration."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class BackendLauncherTests(unittest.TestCase):
    def test_external_cwd_and_developer_settings_do_not_change_tariff_tests(self):
        environment = dict(os.environ)
        environment.update(
            SCOPE_GUARD_LLM_INPUT_RATE_BOUND="0.01",
            SCOPE_GUARD_LLM_OUTPUT_RATE_BOUND="0.02",
            OPENAI_API_KEY="synthetic-launcher-regression",
            PYTHON_DOTENV_DISABLED="0",
        )
        with tempfile.TemporaryDirectory(prefix="scg-launcher-regression-") as directory:
            Path(directory, ".env").write_text(
                "SCOPE_GUARD_LLM_INPUT_RATE_BOUND=0.03\nSCOPE_GUARD_LLM_OUTPUT_RATE_BOUND=0.04\n"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/test_backend.py"),
                    "tests/unit/test_llm_tariff_provenance.py",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                ],
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("2 passed", result.stdout)


if __name__ == "__main__":
    unittest.main()

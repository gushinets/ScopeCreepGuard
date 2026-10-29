"""Exercise PR policy against disposable Git histories, not the developer checkout."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ci/scripts/require-rebase.sh"
INTEGRATION = "codex/any-758-email-verification-password-reset"


def bash_executable():
    if os.name == "nt":
        git_bash = Path(shutil.which("git")).resolve().parents[1] / "bin/bash.exe"
        if git_bash.exists():
            return str(git_bash)
    return "bash"


class BranchPolicyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="scg-policy-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.remote = self.root / "origin.git"
        self.checkout = self.root / "checkout"
        self.checkout.mkdir()
        self.git("init", "--bare", str(self.remote))
        self.git("init", "-b", "main")
        self.git("config", "user.name", "CI fixture")
        self.git("config", "user.email", "ci@example.test")
        self.git("config", "commit.gpgsign", "false")
        self.git("remote", "add", "origin", str(self.remote))
        self.commit("base")
        self.git("push", "origin", "main")
        self.git("checkout", "-b", INTEGRATION)
        self.commit("integration")
        self.git("push", "origin", INTEGRATION)

    def git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.checkout,
            text=True,
            capture_output=True,
            check=True,
            timeout=20,
        ).stdout.strip()

    def commit(self, name):
        (self.checkout / (name + ".txt")).write_text(name)
        self.git("add", ".")
        self.git("commit", "-m", name)
        return self.git("rev-parse", "HEAD")

    def policy(self, base, head=None):
        return subprocess.run(
            [bash_executable(), SCRIPT.as_posix(), base, head or self.git("rev-parse", "HEAD")],
            cwd=self.checkout,
            text=True,
            capture_output=True,
            timeout=30,
        )

    def task(self, base):
        self.git("checkout", "-b", "task", base)
        return self.commit("task")

    def test_current_linear_main_head_passes(self):
        head = self.task("main")
        result = self.policy("main", head)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_main_head_missing_current_base_fails(self):
        head = self.task("main")
        self.git("checkout", "main")
        self.commit("new-main")
        self.git("push", "origin", "main")
        self.assertNotEqual(self.policy("main", head).returncode, 0)

    def test_main_policy_rejects_real_merge(self):
        self.task("main")
        self.git("checkout", "-b", "side", "main")
        self.commit("side")
        self.git("checkout", "task")
        self.git("merge", "--no-ff", "side", "-m", "merge side")
        self.assertNotEqual(self.policy("main").returncode, 0)

    def test_current_linear_integration_head_passes(self):
        head = self.task(INTEGRATION)
        result = self.policy(INTEGRATION, head)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_stale_integration_head_fails(self):
        head = self.task(INTEGRATION)
        self.git("checkout", INTEGRATION)
        self.commit("integration-update")
        self.git("push", "origin", INTEGRATION)
        self.assertNotEqual(self.policy(INTEGRATION, head).returncode, 0)

    def test_merge_based_integration_sync_passes(self):
        self.task(INTEGRATION)
        self.git("checkout", INTEGRATION)
        self.commit("integration-update")
        self.git("push", "origin", INTEGRATION)
        self.git("checkout", "task")
        self.git("merge", "--no-ff", INTEGRATION, "-m", "sync integration")
        result = self.policy(INTEGRATION)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_synthetic_checkout_merge_is_not_the_main_pr_head(self):
        head = self.task("main")
        self.git("checkout", "-b", "checkout-merge", "main")
        self.git("merge", "--no-ff", "task", "-m", "synthetic PR merge")
        result = self.policy("main", head)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_untrusted_base_cannot_execute_shell_text(self):
        result = self.policy("main; touch injected")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.checkout / "injected").exists())

    def test_untrusted_head_cannot_execute_shell_text(self):
        result = self.policy("main", "$(touch injected)")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.checkout / "injected").exists())

    def test_unsupported_base_is_not_a_policy_bypass(self):
        self.git("branch", "unconfigured")
        self.git("push", "origin", "unconfigured")
        self.assertNotEqual(self.policy("unconfigured").returncode, 0)


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.load(
            (ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader
        )

    def test_integration_and_main_prs_are_validated(self):
        triggers = self.workflow["on"]
        self.assertEqual(set(triggers["pull_request"]["branches"]), {"main", INTEGRATION})
        self.assertEqual(set(triggers["push"]["branches"]), {"main", "codex/**"})

    def test_all_pr_jobs_validate_the_combined_checkout(self):
        for name, job in self.workflow["jobs"].items():
            checkout = next(
                step
                for step in job["steps"]
                if step.get("uses", "").startswith("actions/checkout@")
            )
            self.assertNotIn("ref", checkout.get("with", {}), name)

    def test_branch_values_are_passed_through_environment(self):
        job = self.workflow["jobs"]["rebase"]
        step = next(step for step in job["steps"] if "require-rebase.sh" in step.get("run", ""))
        self.assertEqual(step["env"]["PR_BASE_REF"], "${{ github.base_ref }}")
        self.assertEqual(step["env"]["PR_HEAD_SHA"], "${{ github.event.pull_request.head.sha }}")
        self.assertNotIn("${{", step["run"])


if __name__ == "__main__":
    unittest.main()

"""Current schema mappings cannot depend on incidental module import order."""

import subprocess
import sys

import pytest


@pytest.mark.parametrize("first", ["workflow", "profiles"])
def test_profile_metadata_is_complete_before_other_mapping_imports(first):
    code = f"""
import importlib
importlib.import_module('scope_guard.database.models.{first}')
from scope_guard.database.models.workflow import WORKFLOW_METADATA
table = WORKFLOW_METADATA.tables['profiles']
before = tuple(table.c.keys())
assert 'onboarding_status' in before and 'onboarding_step' in before
assert not table.c.onboarding_status.nullable
assert not table.c.onboarding_step.nullable
assert str(table.c.onboarding_status.server_default.arg) == "'not_started'::text"
assert str(table.c.onboarding_step.server_default.arg) == '0'
from scope_guard.database.models.profiles import profiles
assert profiles is table
assert tuple(table.c.keys()) == before
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

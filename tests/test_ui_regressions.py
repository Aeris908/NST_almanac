"""Проверки клиентской логики на настоящем JavaScript-движке."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_client_routes_and_escaping():
    node = shutil.which("node")
    if not node:
        pytest.skip("для клиентских проверок нужен Node.js")
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run([node, "tests/ui_regressions.cjs"], cwd=root,
                            capture_output=True, text=True, encoding="utf-8", check=False)
    assert result.returncode == 0, result.stderr

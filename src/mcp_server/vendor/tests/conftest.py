"""Run the vendored gate suite from the asset root, the layout its relative paths were written for."""
from pathlib import Path

import pytest

ASSET_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _run_from_asset_root(monkeypatch):
    monkeypatch.chdir(ASSET_ROOT)

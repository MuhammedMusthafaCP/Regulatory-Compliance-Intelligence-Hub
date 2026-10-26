import os
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PARSED = ROOT / "data/parsed/gdpr"


def pytest_collection_modifyitems(config, items):
    if os.environ.get("RUN_INTEGRATION") == "1":
        return
    skip = pytest.mark.skip(reason="integration test: set RUN_INTEGRATION=1 (needs DB + models)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def parsed_copy(tmp_path):
    """A scratch copy of the parsed inputs so chunker runs never touch the committed outputs."""
    for name in ("articles.json", "recitals.json", "parse_report.json"):
        shutil.copy(PARSED / name, tmp_path / name)
    return tmp_path

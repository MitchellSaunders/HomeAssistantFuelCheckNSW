from __future__ import annotations

import json
from pathlib import Path


def test_manifest_metadata_has_no_placeholder_values():
    manifest_path = Path("custom_components/nsw_fuel/manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert "yourname" not in manifest["documentation"]
    assert "yourname" not in manifest["issue_tracker"]
    assert "@yourname" not in manifest["codeowners"]

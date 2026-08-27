"""Test import paths for the monorepo source layout."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (
    ROOT / "apps" / "api" / "src",
    ROOT / "packages" / "analytics" / "src",
    ROOT / "packages" / "connectors" / "src",
    ROOT / "packages" / "domain" / "src",
    ROOT / "packages" / "persistence" / "src",
)

for source_root in SOURCE_ROOTS:
    sys.path.insert(0, str(source_root))

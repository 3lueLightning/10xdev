"""Make the skills' scripts importable from tests."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "quality-gates" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "project-scaffold" / "scripts"))

REPO_ROOT = ROOT

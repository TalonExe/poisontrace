"""Start both local PoisonTrace services."""

from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from poisontrace.launcher import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

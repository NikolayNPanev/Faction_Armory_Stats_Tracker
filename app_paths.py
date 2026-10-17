import os
import sys
from pathlib import Path


APP_NAME = "FactionArmoryStatsTracker"


def get_app_data_dir():
    """Return the source directory in development or the user's data directory."""
    running_from_bazel = bool(
        os.environ.get("RUNFILES_DIR") or os.environ.get("RUNFILES_MANIFEST_FILE")
    )
    if not getattr(sys, "frozen", False) and not running_from_bazel:
        return Path(__file__).resolve().parent

    if sys.platform == "win32":
        data_root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        data_root = Path.home() / "Library" / "Application Support"
    else:
        data_root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    app_data_dir = data_root / APP_NAME
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir

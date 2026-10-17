import os
import platform
import shutil
import subprocess
from pathlib import Path

from PyInstaller.__main__ import run as run_pyinstaller


def _find_iscc():
    compiler = shutil.which("ISCC.exe") or shutil.which("iscc")
    if compiler:
        return compiler

    candidates = (
        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        / "Programs"
        / "Inno Setup 6"
        / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
        / "Inno Setup 6"
        / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
        / "Inno Setup 7"
        / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        / "Inno Setup 7"
        / "ISCC.exe",
    )
    return next((str(path) for path in candidates if path.is_file()), None)


def main():
    if platform.system() != "Windows":
        raise RuntimeError("The standalone Setup installer can only be built on Windows.")

    project_dir = Path(
        os.environ.get("BUILD_WORKSPACE_DIRECTORY", Path(__file__).resolve().parent)
    ).resolve()
    output_dir = project_dir / "dist" / "windows"
    work_dir = project_dir / "bazel-bin" / "pyinstaller-work"
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    run_pyinstaller([
        str(project_dir / "app_main.py"),
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "FactionArmoryStatsTracker",
        "--distpath",
        str(output_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(work_dir),
        "--paths",
        str(project_dir),
    ])

    compiler = _find_iscc()
    if compiler is None:
        raise RuntimeError(
            "Inno Setup 6 or 7 is required. Install it and make ISCC.exe available on PATH."
        )

    installer_script = project_dir / "installer.iss"
    subprocess.run([compiler, str(installer_script)], cwd=project_dir, check=True)
    installer = project_dir / "dist" / "installer" / "FactionArmoryStatsTracker-Setup.exe"
    print(f"Created installer: {installer}")


if __name__ == "__main__":
    main()

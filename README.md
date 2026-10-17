# Faction_Armory_Stats_Tracker
Tracker for average armory item usage and statistics

## Install and run (Windows)

Download and run [FactionArmoryStatsTracker-Setup.exe from GitHub Releases](https://github.com/NikolayNPanev/Faction_Armory_Stats_Tracker/releases). The installer is per-user and does not need administrator access. Choose whether to create a desktop shortcut, then launch **Faction Armory Stats Tracker** from the Start Menu. On the first refresh, enter your Torn API key. The key and armory data stay in your Windows user profile and are not removed when the app is uninstalled.

If no release installer is available yet, use the source setup below. It requires Python 3.11.

1. Install Python 3.11 from [python.org](https://www.python.org/downloads/). In the installer, enable **Add python.exe to PATH**.
2. Download this repository as a ZIP using the green **Code** button, then extract the ZIP.
3. Open PowerShell in the extracted `Faction_Armory_Stats_Tracker` folder. In File Explorer, open that folder, click the address bar, type `powershell`, and press Enter.
4. Set up the app and start it by running these commands one at a time:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe gui.py
```

The first time you click **Reload Latest Data**, the app asks for your Torn API key and saves it in your Windows user settings. The key is not included in the project or sent anywhere except Torn's API. The key needs access to faction inventory and organized-crime definitions. With this source install, exports and saved thresholds are stored in the project's `OUTPUT` folder.

To open the app again later, repeat only the last command from the extracted folder:

```powershell
.\.venv\Scripts\python.exe gui.py
```

## Build with Bazel (developers)

Install [Bazelisk](https://github.com/bazelbuild/bazelisk). Bazelisk reads `.bazelversion` and selects the pinned Bazel version automatically. From the repository folder:

```powershell
bazel build //:app
bazel run //:app
bazel run //:windows_installer
python -m unittest app_paths_test.py
```

`bazel run //:windows_installer` requires Inno Setup 6 or 7 installed on the build machine. It writes `dist/installer/FactionArmoryStatsTracker-Setup.exe`. The GitHub release workflow installs Inno Setup, builds the installer on Windows, and attaches it to `v*` tag releases. The Windows CI workflow runs the smoke test and Bazel app build. `bazel test //...` is also available, but on Windows it requires symbolic-link privileges for rules_python's hermetic test environment.

The installer's bundled executable is Windows-native.

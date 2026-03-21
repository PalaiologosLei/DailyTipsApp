# Windows 1.0 Release

## Build once

```powershell
npm install
npm run build:windows
```

This does two things:

1. Runs `scripts/prepare_release_resources.ps1`
2. Builds the Tauri installer

The default installer output paths are:

- `src-tauri/target/release/bundle/nsis/DailyTipsApp_0.1.0_x64-setup.exe`
- `src-tauri/target/release/bundle/msi/`

For a faster release that only builds the NSIS installer:

```powershell
npm run build:windows:nsis
```

## What gets bundled

The release resource staging script copies these into `src-tauri/resources/`:

- `src/`
- `assets/backgrounds/default/`
- `vendor/tectonic/`
- a Python runtime under `python-runtime/`

The packaged app then prefers those bundled resources at runtime.

## Python runtime source

By default the resource script tries these Python executables in order:

1. `-PythonExe` argument
2. `DAILYTIPS_PYTHON_EXE`
3. `D:\Applications\miniconda\python.exe`
4. `python` from `PATH`

To build with a specific Python runtime:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\prepare_release_resources.ps1 -PythonExe "D:\Path\To\python.exe"
```

Then build:

```powershell
npx tauri build --bundles nsis
```

## Verification checklist

Before publishing, test the generated installer on a clean Windows machine:

1. Install the app using the generated `*-setup.exe`
2. Launch the app
3. Confirm Tectonic is detected in the runtime status
4. Choose a local Markdown directory
5. Generate wallpapers into an iCloud/OneDrive test folder
6. Confirm `images_index.json` and PNG files are created

## Notes

- `src-tauri/resources/` is generated and should not be edited by hand.
- Re-run the resource script whenever Python dependencies or bundled resources change.
- If you later replace the Python renderer completely, you can remove the `python-runtime/` staging step from the script and from `tauri.conf.json`.

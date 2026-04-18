# BeeHQ for Windows

This folder exists to make the Windows side easier to find when you upload the repo to GitHub.

## What BeeHQ already has for Windows

- Windows build workflow:
  - `.github/workflows/build-windows.yml`
- Windows PyInstaller spec:
  - `packaging/BeeHQ-windows.spec`
- Windows local build script:
  - `scripts/build_windows_app.ps1`

## How to get a Windows build from GitHub

1. Push the newest code to GitHub.
2. Open your repo on GitHub.
3. Go to `Actions`.
4. Run `Build Windows App`.
5. Download the `BeeHQ-windows` artifact.
6. Extract it and run `BeeHQ.exe`.

## Important note about hourly rankings

BeeHQ can rank accounts by hourly rate from:

1. parsed text updates, and now also
2. OCR fallback from the hourly report image

The OCR fallback is best-effort and depends on the hourly image being readable enough.
If you want the OCR to work best on your machine, install Tesseract:

- Windows:
  - install Tesseract OCR
  - make sure `tesseract.exe` is available in PATH

Without Tesseract, BeeHQ still works, but the OCR-based image ranking fallback will not run.

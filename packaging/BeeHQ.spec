# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


ROOT = Path.cwd()
APP_NAME = "BeeHQ"

datas = []
datas += collect_data_files("customtkinter")
datas += collect_data_files("PIL")
datas += [(str(ROOT / ".env.example"), ".")]
if (ROOT / "assets").exists():
    datas += [(str(ROOT / "assets"), "assets")]

hiddenimports = []
hiddenimports += collect_submodules("discord")
hiddenimports += collect_submodules("customtkinter")
hiddenimports += collect_submodules("PIL")
hiddenimports += collect_submodules("dotenv")


a = Analysis(
    ["app/main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon=None,
    bundle_identifier="com.beehq.dashboard",
    info_plist={
        "CFBundleName": "BeeHQ",
        "CFBundleDisplayName": "BeeHQ",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
    },
)

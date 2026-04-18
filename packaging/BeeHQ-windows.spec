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
hiddenimports += collect_submodules("plyer")


a = Analysis(
    [str(ROOT / "app" / "main.py")],
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

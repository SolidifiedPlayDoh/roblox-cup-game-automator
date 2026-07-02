# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("customtkinter")
asset_dir = Path("cup_guard/assets")
datas += [(str(p), f"cup_guard/assets/{p.name}") for p in asset_dir.glob("*.png")]

a = Analysis(
    ["cup_guard/__main__.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["PIL._tkinter_finder"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CupGuard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CupGuard",
)

app = BUNDLE(
    coll,
    name="CupGuard.app",
    icon=None,
    bundle_identifier="com.solidifiedplaydoh.cupguard",
)

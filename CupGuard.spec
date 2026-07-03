# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

import tkinter
from PyInstaller.utils.hooks import collect_all

base = Path(sys.base_prefix)
tk_pkg = Path(tkinter.__file__).parent

datas, binaries, hiddenimports = collect_all("customtkinter")
asset_dir = Path("cup_guard/assets")
datas += [(str(p), f"cup_guard/assets/{p.name}") for p in asset_dir.glob("*.png")]
datas += [(str(tk_pkg), "tkinter")]

for tcl_name, tk_name in (("tcl9.0", "tk9.0"), ("tcl8.6", "tk8.6")):
    tcl_dir = base / "lib" / tcl_name
    tk_dir = base / "lib" / tk_name
    if tcl_dir.is_dir():
        datas += [(str(tcl_dir), f"lib/{tcl_name}")]
    if tk_dir.is_dir():
        datas += [(str(tk_dir), f"lib/{tk_name}")]

hiddenimports += ["tkinter", "_tkinter", "PIL._tkinter_finder", "Quartz", "objc"]

a = Analysis(
    ["cup_guard/__main__.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        "cup_guard/pyi_rth_crash.py",
        "cup_guard/pyi_rth_tkinter.py",
    ],
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
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name="CupGuard",
)

app = BUNDLE(
    coll,
    name="CupGuard.app",
    icon=None,
    bundle_identifier="com.solidifiedplaydoh.cupguard",
    info_plist={
        "CFBundleShortVersionString": "1.1.1",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
    },
)

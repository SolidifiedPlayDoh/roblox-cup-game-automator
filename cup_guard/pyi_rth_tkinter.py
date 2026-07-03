"""PyInstaller runtime hook: point Tcl/Tk at bundled script libs inside the .app."""
import os
import sys
from pathlib import Path


def _tcl_tk_dirs() -> tuple[Path | None, Path | None]:
    lib_roots: list[Path] = []
    if sys.platform == "darwin":
        # macOS .app stores datas under Contents/Resources; Frameworks/lib symlinks there.
        resources = Path(sys.executable).resolve().parent.parent / "Resources" / "lib"
        lib_roots.append(resources)
    if getattr(sys, "frozen", False):
        lib_roots.append(Path(sys._MEIPASS) / "lib")

    for lib_root in lib_roots:
        for tcl_name, tk_name in (("tcl9.0", "tk9.0"), ("tcl8.6", "tk8.6")):
            tcl = lib_root / tcl_name
            tk = lib_root / tk_name
            if tcl.is_dir() and tk.is_dir():
                return tcl, tk
    return None, None


if getattr(sys, "frozen", False):
    tcl_dir, tk_dir = _tcl_tk_dirs()
    if tcl_dir is not None:
        os.environ["TCL_LIBRARY"] = str(tcl_dir)
    if tk_dir is not None:
        os.environ["TK_LIBRARY"] = str(tk_dir)

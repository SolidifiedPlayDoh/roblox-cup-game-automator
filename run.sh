#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# uv-managed Python on macOS ships Tcl/Tk but hardcodes broken search paths.
if [[ "$(uname -s)" == "Darwin" ]] && [[ -z "${TCL_LIBRARY:-}" ]]; then
  py_root="$(uv python find 3.12 2>/dev/null || true)"
  if [[ -n "$py_root" && -d "${py_root%/bin/python}/lib/tcl9.0" ]]; then
    py_lib="${py_root%/bin/python}/lib"
    export TCL_LIBRARY="${py_lib}/tcl9.0"
    export TK_LIBRARY="${py_lib}/tk9.0"
  fi
fi

if [ "$#" -eq 0 ]; then
  exec uv run --python 3.12 cup-guard
fi
exec uv run --python 3.12 cup-guard "$@"

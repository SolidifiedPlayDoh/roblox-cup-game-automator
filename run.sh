#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# uv-managed Python on macOS ships Tcl/Tk but hardcodes broken search paths.
if [[ "$(uname -s)" == "Darwin" ]] && [[ -z "${TCL_LIBRARY:-}" ]]; then
  py_prefix="$(uv run --python 3.12 python -c "import sys; print(sys.base_prefix)" 2>/dev/null || true)"
  if [[ -n "$py_prefix" && -d "${py_prefix}/lib/tcl9.0" ]]; then
    export TCL_LIBRARY="${py_prefix}/lib/tcl9.0"
    export TK_LIBRARY="${py_prefix}/lib/tk9.0"
  fi
fi

if [ "$#" -eq 0 ]; then
  exec uv run --python 3.12 cup-guard
fi
exec uv run --python 3.12 cup-guard "$@"

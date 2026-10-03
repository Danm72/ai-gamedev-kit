#!/bin/bash
# Starts the MCP server with a local venv. It builds the venv when it is missing or has no `mcp` package
# (a fresh clone or worktree, or a half-built venv), so no manual step is needed.
cd "$(dirname "$0")"
venv_ok() { [ -x .venv/bin/python ] && .venv/bin/python -I -c "import mcp.server.mcpserver" 2>/dev/null; }
if ! venv_ok; then
  # One builder at a time: parallel runs in one folder wait for the first (stale lock after 120 s).
  for _ in $(seq 24); do mkdir .venv.lock 2>/dev/null && break; sleep 5; done
  trap 'rmdir .venv.lock 2>/dev/null' EXIT
  if ! venv_ok; then
    rm -rf .venv
    # Agent and hook shells often lack ~/.local/bin, so look for uv there too.
    UV=$(command -v uv || ls "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" /opt/homebrew/bin/uv 2>/dev/null | head -1)
    if [ -n "$UV" ]; then
      "$UV" venv -q .venv --python 3.12 >&2 && "$UV" pip install -q --python .venv/bin/python -r requirements.txt >&2
    else
      # No uv: the stdlib venv with a Python new enough for `mcp`.
      PY=$(command -v python3.13 python3.12 python3.11 python3.10 | head -1)
      "${PY:-python3}" -m venv .venv >&2 && .venv/bin/python -m pip install -q -r requirements.txt >&2
    fi
    venv_ok || { echo "run.sh: could not build .venv (uv: ${UV:-none})" >&2; exit 1; }
  fi
  rmdir .venv.lock 2>/dev/null
  trap - EXIT
fi
exec .venv/bin/python server.py

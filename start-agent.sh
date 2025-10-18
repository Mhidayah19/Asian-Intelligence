#!/bin/bash

set -e

# Always run from repo root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/agent"

# 1) Ensure a local virtual environment exists at agent/.venv
if [ ! -x ".venv/bin/python" ]; then
  echo "Creating virtual environment at agent/.venv ..."
  python3 -m venv .venv
fi

# 2) Select Python interpreter (allow override via $PYTHON_BIN)
if [ -z "${PYTHON_BIN:-}" ]; then
  if [ -x "./.venv/bin/python" ]; then
    PYTHON_BIN="./.venv/bin/python"
  elif [ -x "../.venv/bin/python" ]; then
    PYTHON_BIN="../.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3 || true)"
  fi
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "Unable to find python3 on PATH. Set PYTHON_BIN to your interpreter and retry."
  exit 1
fi

echo "Using Python: $PYTHON_BIN"

# 3) Install dependencies (try normal install, then fallback with trusted hosts if SSL blocks)
echo "Installing Python dependencies..."
set +e
"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
"$PYTHON_BIN" -m pip install -r requirements.txt
INSTALL_RC=$?
if [ $INSTALL_RC -ne 0 ]; then
  echo "pip install failed (rc=$INSTALL_RC). Retrying with trusted-host fallback..."
  PIP_NO_CACHE_DIR=1 "$PYTHON_BIN" -m pip install \
    --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    --index-url https://pypi.org/simple \
    -r requirements.txt
  INSTALL_RC=$?
fi
set -e

if [ $INSTALL_RC -ne 0 ]; then
  echo "Dependency installation failed. Please check your network/SSL settings."
  exit $INSTALL_RC
fi

# 4) Provide a safe CPU count to avoid psutil sysctl issues in restricted environments
if [ -z "${LIVEKIT_CPU_COUNT:-}" ]; then
  # Prefer sysctl if available; otherwise fallback to 2
  if command -v sysctl >/dev/null 2>&1; then
    LIVEKIT_CPU_COUNT="$(sysctl -n hw.logicalcpu 2>/dev/null || echo 2)"
  else
    LIVEKIT_CPU_COUNT=2
  fi
  export LIVEKIT_CPU_COUNT
fi
# Set additional aliases some libraries may honor
export AGENTS_CPU_COUNT="${AGENTS_CPU_COUNT:-$LIVEKIT_CPU_COUNT}"
export CPU_COUNT="${CPU_COUNT:-$LIVEKIT_CPU_COUNT}"

echo "CPU count for agent: $LIVEKIT_CPU_COUNT"

# 5) Download required models (first time only)
if [ ! -d ".livekit" ]; then
  echo "Downloading AI models..."
  "$PYTHON_BIN" src/agent.py download-files
fi

# 6) Run the agent
echo "Starting agent..."
"$PYTHON_BIN" src/agent.py dev

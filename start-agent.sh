#!/bin/bash
cd agent

# Use an overridable Python interpreter, preferring local virtualenv
if [ -z "$PYTHON_BIN" ]; then
  if [ -x "../.venv/bin/python" ]; then
    PYTHON_BIN="../.venv/bin/python"
  elif [ -x ".venv/bin/python" ]; then
    PYTHON_BIN="./.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3 || true)"
  fi
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "Unable to find python3 on PATH. Set PYTHON_BIN to your interpreter and retry."
  exit 1
fi

echo "Starting agent with Python: $PYTHON_BIN"

# Download required models (first time only)
if [ ! -d ".livekit" ]; then
    echo "Downloading AI models..."
    $PYTHON_BIN src/agent.py download-files
fi

# Run the agent
$PYTHON_BIN src/agent.py dev

#!/bin/bash
cd agent

# Use the Python where we installed packages
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11"

echo "Starting UNIFIED agent (auto-switching voice/vision) with Python: $PYTHON_BIN"

# Download required models (first time only)
if [ ! -d ".livekit" ]; then
    echo "Downloading AI models..."
    $PYTHON_BIN src/unified_agent.py download-files
fi

# Run the UNIFIED agent (automatic voice-only / vision mode switching)
$PYTHON_BIN src/unified_agent.py dev

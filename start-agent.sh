#!/bin/bash
cd agent

# Use the Python where we installed packages
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11"

echo "Starting agent with Python: $PYTHON_BIN"

# Download required models (first time only)
if [ ! -d ".livekit" ]; then
    echo "Downloading AI models..."
    $PYTHON_BIN src/agent.py download-files
fi

# Run the agent
$PYTHON_BIN src/agent.py dev

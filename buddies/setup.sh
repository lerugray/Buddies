#!/bin/bash
echo "============================================"
echo "  BUDDIES - First Time Setup"
echo "============================================"
echo ""

echo "[1/3] Installing Buddies..."
pip install -e . > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "FAILED: Could not install. Make sure Python 3.11+ and pip are installed."
    exit 1
fi
echo "      Done!"

echo "[2/3] Registering Claude Code hooks..."
python -m buddies.setup_hooks > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "      Skipped - Claude Code hooks not available"
else
    echo "      Done!"
fi

echo "[3/3] Registering MCP tools..."
python -m buddies.setup_mcp > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "      Skipped - MCP setup not available"
else
    echo "      Done!"
fi

echo ""
echo "============================================"
echo "  Setup complete! Run ./launch.sh to start."
echo "============================================"
echo ""
echo "TIP: To connect a local AI model, install Ollama"
echo "from https://ollama.com and run:"
echo "  ollama pull llama3.2:3b"
echo ""

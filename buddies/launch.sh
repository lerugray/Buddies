#!/bin/bash
echo "Starting Buddies..."
python -m buddies
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Could not start Buddies."
    echo "Make sure Python 3.11+ is installed and you've run setup.sh first."
    echo ""
    read -p "Press Enter to close..."
fi

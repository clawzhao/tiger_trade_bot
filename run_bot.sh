#!/bin/bash
# Tiger Trade Bot - Main Runner

set -e

echo "🐯📈 Tiger Trade Bot"
echo "===================="

# Check if running in the correct directory
if [ ! -f "config.py" ]; then
    echo "❌ Error: Please run this script from the tiger_trade_bot root directory"
    exit 1
fi

# Check for config_local.py
if [ ! -f "config_local.py" ]; then
    echo "❌ config_local.py not found!"
    echo "Please set up your credentials first:"
    echo "  cp config_local.py.example config_local.py"
    echo "Then edit config_local.py with your Tiger credentials."
    echo ""
    exit 1
fi

# Check for private key
if [ ! -f "keys/rsa_private_key.pem" ]; then
    echo "❌ Private key not found at keys/rsa_private_key.pem"
    exit 1
fi

# Install dependencies if needed
if ! python3 -c "import tigeropen" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    python3 -m pip install -r requirements.txt
fi

# Run bot
echo "🚀 Starting bot..."
python3 -m tiger_trade_bot "$@"
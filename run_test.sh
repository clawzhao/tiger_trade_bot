#!/bin/bash
# Tiger Trade Bot - Connectivity Test Runner

set -e

echo "🐯📈 Tiger Trade Bot - Connectivity Test"
echo "========================================"

# Check if running in the correct directory
if [ ! -f "config.py" ]; then
    echo "❌ Error: Please run this script from the tiger_trade_bot root directory"
    exit 1
fi

# Check if config_local.py exists, if not prompt user
if [ ! -f "config_local.py" ]; then
    echo "⚠️  config_local.py not found"
    echo "Please copy config_local.py.example and fill in your credentials:"
    echo "  cp config_local.py.example config_local.py"
    echo ""
    echo "Then edit config_local.py with:"
    echo "  - TIGER_ID (from https://developer.itigerup.com/)"
    echo "  - ACCOUNT_ID (17-digit paper trading account)"
    echo "  - PRIVATE_KEY_PATH (./keys/rsa_private_key.pem)"
    echo ""
    exit 1
fi

# Check for private key
if [ ! -f "keys/rsa_private_key.pem" ]; then
    echo "❌ Private key not found at keys/rsa_private_key.pem"
    echo "Please place your RSA private key there."
    echo ""
    echo "To generate the key:"
    echo "  1. Go to https://developer.itigerup.com/"
    echo "  2. Click 'Generate Key' and copy the PRIVATE KEY"
    echo "  3. Save it as keys/rsa_private_key.pem"
    echo ""
    exit 1
fi

# Check Python and pip
echo "🔍 Checking Python dependencies..."
python3 -m pip install --upgrade pip > /dev/null 2>&1
if ! python3 -c "import tigeropen" 2>/dev/null; then
    echo "📦 Installing tigeropen SDK..."
    python3 -m pip install -r requirements.txt
fi
echo "✅ Dependencies ready"

# Run the test
echo ""
echo "🧪 Running connectivity test..."
python3 tests/test_tiger_connectivity.py
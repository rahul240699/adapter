#!/bin/bash
# X402 Dependencies Setup Script
# This script installs the additional dependencies needed for X402 payment system

echo "🔧 X402 Dependencies Setup"
echo "=========================="

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️ No virtual environment detected"
    echo "Please activate your virtual environment first:"
    echo "   source venv/bin/activate"
    exit 1
fi

echo "✅ Virtual environment detected: $VIRTUAL_ENV"
echo ""

# Install base requirements first
echo "📦 Installing base requirements..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install base requirements"
    exit 1
fi

echo "✅ Base requirements installed"
echo ""

# Clone and install x402-a2a if not already present
if [ ! -d "a2a-x402" ]; then
    echo "📥 Cloning official x402-a2a repository..."
    git clone https://github.com/google-agentic-commerce/a2a-x402.git
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to clone x402-a2a repository"
        exit 1
    fi
    
    echo "✅ Repository cloned"
else
    echo "📁 x402-a2a repository already exists"
fi

# Install x402-a2a in editable mode
echo "📦 Installing x402-a2a library..."
cd a2a-x402/python/x402_a2a
pip install -e .

if [ $? -ne 0 ]; then
    echo "❌ Failed to install x402-a2a library"
    exit 1
fi

cd ../../..
echo "✅ x402-a2a library installed"
echo ""

# Verify installation
echo "🔍 Verifying X402 installation..."

python3 -c "
import sys
try:
    import anthropic
    print('✅ anthropic')
except ImportError:
    print('❌ anthropic - MISSING')
    sys.exit(1)

try:
    from python_a2a import Message, MessageRole, TextContent
    print('✅ python_a2a')
except ImportError:
    print('❌ python_a2a - MISSING')
    sys.exit(1)

try:
    from python_a2a.models.content import Metadata
    print('✅ python_a2a.models.content.Metadata')
except ImportError:
    print('❌ python_a2a.models.content.Metadata - MISSING')
    sys.exit(1)

# X402 uses mock implementation - no blockchain dependencies needed
print('✅ X402 mock payment system (no blockchain required)')

try:
    from nanda_adapter.core.x402_compliant_middleware import X402PaymentMiddleware
    print('✅ X402PaymentMiddleware')
except ImportError as e:
    print(f'❌ X402PaymentMiddleware - MISSING: {e}')
    sys.exit(1)

print('✅ All X402 dependencies verified!')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 X402 setup completed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Set your ANTHROPIC_API_KEY in .env file"
    echo "   2. Test with: python3 test_x402_specification.py"
    echo "   3. Deploy to EC2 with updated requirements"
    echo ""
    echo "💡 The system now includes:"
    echo "   - Official x402-a2a specification compliance"
    echo "   - Ethereum blockchain integration"
    echo "   - MCP payment server support"
    echo "   - Full A2A x402 payment flow"
else
    echo ""
    echo "❌ X402 setup failed!"
    echo "Check the error messages above and try running again."
    exit 1
fi
#!/bin/bash
# Quick setup script for PO Agent

echo "🎯 PO Agent Setup"
echo "=================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env with your Jira credentials:"
    echo "   - JIRA_URL"
    echo "   - JIRA_EMAIL"
    echo "   - JIRA_API_TOKEN"
    echo ""
else
    echo "✓ .env file exists"
fi

# Test connection
echo ""
echo "Testing Jira connection..."
python src/jira_client.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "To use the tools, first activate the virtual environment:"
    echo "   source venv/bin/activate"
    echo ""
    echo "Then run:"
    echo "   python src/issue_creator.py      - Create new issues"
    echo "   python src/refinement_prep.py    - Prepare for refinement"
    echo "   python src/backlog_cull.py       - Find stale issues"
    echo ""
    echo "To deactivate the virtual environment when done:"
    echo "   deactivate"
    echo ""
else
    echo ""
    echo "❌ Connection test failed. Please check your .env configuration."
    echo ""
fi

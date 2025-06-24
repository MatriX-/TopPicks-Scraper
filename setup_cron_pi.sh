#!/bin/bash

echo "🍓 Setting up TopPicks Scraper on Raspberry Pi..."
echo "================================================"

# Get the current directory (where the script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/generate_parlays.py"

echo "📁 Script directory: $SCRIPT_DIR"
echo "🐍 Python script: $PYTHON_SCRIPT"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python3 first:"
    echo "   sudo apt update && sudo apt install python3 python3-pip"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Installing pip3..."
    sudo apt update && sudo apt install python3-pip
fi

echo ""
echo "📦 Installing Python dependencies..."
pip3 install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "⏰ Setting up cron job (every 30 minutes)..."

# Create the cron job entry
CRON_JOB="*/30 * * * * cd $SCRIPT_DIR && /usr/bin/python3 $PYTHON_SCRIPT >> $SCRIPT_DIR/cron.log 2>&1"

# Check if the cron job already exists
if crontab -l 2>/dev/null | grep -q "$PYTHON_SCRIPT"; then
    echo "⚠️  Cron job already exists. Removing old one..."
    crontab -l 2>/dev/null | grep -v "$PYTHON_SCRIPT" | crontab -
fi

# Add the new cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Summary:"
echo "   • Cron job created to run every 30 minutes"
echo "   • Logs will be saved to: $SCRIPT_DIR/cron.log"
echo "   • Script will run: $PYTHON_SCRIPT"
echo ""
echo "🔧 To manage the cron job:"
echo "   • View all cron jobs: crontab -l"
echo "   • Edit cron jobs: crontab -e"
echo "   • Remove this job: crontab -l | grep -v generate_parlays.py | crontab -"
echo ""
echo "📊 To check if it's working:"
echo "   • View logs: tail -f $SCRIPT_DIR/cron.log"
echo "   • Test manually: cd $SCRIPT_DIR && python3 generate_parlays.py"
echo ""
echo "🎉 Your TopPicks scraper will now run automatically every 30 minutes!" 
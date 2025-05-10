#!/bin/bash

set -e

echo "🔧 Activating virtual environment..."
source .venv/bin/activate

echo "📦 Installing required Python packages..."
pip install -r requirements.txt

echo "📝 Updating requirements.txt..."
pip freeze > requirements.txt

echo "🚀 Running your application..."
python3 -m src.main

echo "✅ Setup and run complete!"

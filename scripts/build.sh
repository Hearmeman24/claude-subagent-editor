#!/bin/bash
# Build script for Claude Subagent Editor

set -e

# Validate prerequisites
if [ ! -d "frontend" ]; then
  echo "Error: frontend directory not found. Run from project root."
  exit 1
fi

if ! command -v npm &> /dev/null; then
  echo "Error: npm not installed. Please install Node.js and npm."
  exit 1
fi

echo "Building React frontend..."
cd frontend
npm install
npm run build

echo "Copying to Python package..."
rm -rf ../src/claude_subagent_editor/static
mkdir -p ../src/claude_subagent_editor/static
cp -r dist/* ../src/claude_subagent_editor/static/

echo "Build complete!"
echo "Run: uv run claude-subagent-editor"

#!/bin/bash
# Build script for Claude Subagent Editor

set -e

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

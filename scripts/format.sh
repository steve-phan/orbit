#!/bin/bash
# Auto-format code

set -e

echo "🎨 Formatting code..."

echo "Running Black..."
black orbit/ tests/

echo "Running Ruff --fix..."
ruff check --fix orbit/ tests/

echo "✅ Code formatted!"

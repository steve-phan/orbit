#!/bin/bash
# Code quality check script

set -e

echo "🔍 Running code quality checks..."

echo ""
echo "1️⃣  Running Ruff (linter)..."
ruff check orbit/ tests/

echo ""
echo "2️⃣  Running Black (formatter check)..."
black --check orbit/ tests/

echo ""
echo "3️⃣  Running MyPy (type checker)..."
mypy orbit/ --ignore-missing-imports

echo ""
echo "4️⃣  Running tests..."
pytest tests/ -v

echo ""
echo "✅ All checks passed!"

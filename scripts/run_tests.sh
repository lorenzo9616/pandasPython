#!/usr/bin/env bash
# =============================================================================
# run_tests.sh — Run the full test suite for the RAG system
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=== Generating sample data ==="
python SampleData/generate_sample.py

echo ""
echo "=== Running Python tests ==="
python -m pytest tests/ -v --tb=short "$@"

echo ""
echo "=== All tests passed ==="

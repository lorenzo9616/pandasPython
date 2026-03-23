#!/usr/bin/env bash
# =============================================================================
# setup.sh — One-command setup for the RAG system
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=== 1/4  Installing Python dependencies ==="
pip install -r requirements.txt

echo ""
echo "=== 2/4  Installing test dependencies ==="
pip install pytest

echo ""
echo "=== 3/4  Generating sample Excel data ==="
cd SampleData && python generate_sample.py && python generate_audit_data.py && python generate_compare_data.py && cd ..

echo ""
echo "=== 4/4  Restoring .NET packages ==="
if command -v dotnet &>/dev/null; then
    cd RagHost && dotnet restore && cd ..
    echo "  .NET restore complete."
else
    echo "  [SKIP] dotnet SDK not found — install .NET 8 SDK to build the C# host."
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  Run tests:        bash scripts/run_tests.sh"
echo "  Run with Docker:  docker compose up rag-app"
echo "  Run with .NET:    cd RagHost && dotnet run -- --file ../SampleData/sales.xlsx --group Category"

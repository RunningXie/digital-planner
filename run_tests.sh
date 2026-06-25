#!/bin/bash
# ============================================
#  Digital Planner Integration Test Runner
#  Run this every time you make changes.
#  Usage: bash run_tests.sh [--no-concurrency]
# ============================================
set -e

echo "=================================="
echo "  Digital Planner - Integration Tests"
echo "=================================="

cd "$(dirname "$0")"

# Check if --no-concurrency flag is provided
NO_CONCURRENCY=false
if [ "$1" = "--no-concurrency" ]; then
    NO_CONCURRENCY=true
    shift
fi

# Set up pip path
PIP="$HOME/.local/bin/pip"
if [ ! -f "$PIP" ]; then
    PIP="pip3"
fi

# Install test dependencies if needed (从 requirements-dev.txt 读单一来源)
echo ""
echo "[1/2] Checking dependencies..."
$PIP install --user --break-system-packages -r requirements-dev.txt -q 2>/dev/null || \
    $PIP install -r requirements-dev.txt -q 2>/dev/null || \
    echo "[WARN] Could not install test dependencies, continuing anyway..."

# Run all tests with concurrency (pytest-xdist)
echo ""
echo "[2/2] Running all tests..."

# Determine number of workers: use CPU count, max 4 for stability
WORKERS=$(nproc 2>/dev/null || echo 2)
if [ "$WORKERS" -gt 4 ]; then
    WORKERS=4
fi

if [ "$NO_CONCURRENCY" = true ]; then
    echo "Running tests sequentially..."
    # Prefer the local venv if available
    if [ -f "venv/bin/python" ]; then
        venv/bin/python -m pytest tests/ -v --tb=short
    else
        python3 -m pytest tests/ -v --tb=short 2>/dev/null || \
            python -m pytest tests/ -v --tb=short
    fi
else
    echo "Running tests with $WORKERS concurrent workers..."
    echo "(Add --no-concurrency to run sequentially)"
    echo ""
    if [ -f "venv/bin/python" ]; then
        venv/bin/python -m pytest tests/ -v --tb=short -n "$WORKERS"
    else
        python3 -m pytest tests/ -v --tb=short -n "$WORKERS" 2>/dev/null || \
            python -m pytest tests/ -v --tb=short -n "$WORKERS"
    fi
fi

echo ""
echo "=================================="
echo "  All tests completed!"
echo "=================================="
#!/bin/sh
# Run the whole backend safety-net test suite with one command:
#   cd backend && sh tests/run_all.sh
# Needs: pip install aiosqlite   (test-only dep — in-memory DB engine)
set -e
cd "$(dirname "$0")/.."
for f in tests/test_*.py; do
  echo "── $f"
  python3 "$f"
done
echo "✅ ALL TEST FILES PASSED"

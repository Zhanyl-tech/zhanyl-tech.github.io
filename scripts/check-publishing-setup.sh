#!/bin/bash
set -e

PYTHON_BIN="python3"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi

MMDC_BIN="mmdc"
if [ -x "node_modules/.bin/mmdc" ]; then
  MMDC_BIN="node_modules/.bin/mmdc"
fi

echo "Publishing setup check"
echo "======================"
echo ""

missing=0

check_python_module() {
  local module="$1"
  if "$PYTHON_BIN" - <<PY >/dev/null 2>&1
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("${module}") else 1)
PY
  then
    echo "OK   Python module: ${module}"
  else
    echo "MISS Python module: ${module}"
    missing=1
  fi
}

check_file() {
  local file="$1"
  if [ -f "$file" ]; then
    echo "OK   File: ${file}"
  else
    echo "MISS File: ${file}"
    missing=1
  fi
}

check_python_module "anthropic"
check_python_module "requests"
check_binary() {
  local bin="$1"
  if [ -x "$bin" ] || command -v "$bin" >/dev/null 2>&1; then
    echo "OK   Binary: ${bin}"
  else
    echo "MISS Binary: ${bin}"
    missing=1
  fi
}

echo "Using Python: ${PYTHON_BIN}"
echo "Using Mermaid CLI: ${MMDC_BIN}"

check_binary "$MMDC_BIN"
check_file "scripts/cope.sh"
check_file "scripts/vizpub.py"

if [ -n "${ANTHROPIC_API_KEY}" ]; then
  echo "OK   ANTHROPIC_API_KEY is set"
else
  echo "MISS ANTHROPIC_API_KEY is not set"
  missing=1
fi

echo ""
if [ "$missing" -eq 0 ]; then
  echo "All publishing dependencies are ready."
  echo "You can run:"
  echo "  ./scripts/cope.sh content/blog/your-post.md"
  echo "  ${PYTHON_BIN} scripts/vizpub.py --topic \"Your topic here\""
else
  echo "Some dependencies are missing."
  echo "Install with:"
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/python -m pip install anthropic requests"
  echo "  npm install -D @mermaid-js/mermaid-cli"
  echo "  export ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

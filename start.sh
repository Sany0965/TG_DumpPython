#!/bin/sh
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c "import aiohttp, telethon, python_socks" 2>/dev/null; then
  .venv/bin/pip install -r requirements.txt
fi
exec .venv/bin/python app.py "$@"

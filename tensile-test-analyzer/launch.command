#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  runtime=""
  for candidate in python3.12 python3.13 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; assert (3,11) <= sys.version_info[:2] < (3,14)' 2>/dev/null; then
      runtime="$candidate"
      break
    fi
  done
  if [ -z "$runtime" ]; then
    echo 'Python 3.11, 3.12 veya 3.13 gerekli / Python 3.11–3.13 required.'
    echo 'https://www.python.org/downloads/'
    exit 1
  fi
  "$runtime" -m venv .venv
fi
if ! cmp -s requirements.txt .venv/installed-requirements.txt; then
  .venv/bin/python -m pip install -r requirements.txt
  cp requirements.txt .venv/installed-requirements.txt
fi
exec .venv/bin/python app.py

#!/bin/zsh
set -eu
cd -- "$(dirname -- "$0")"

if ! command -v npm >/dev/null 2>&1; then
  echo 'Za web interfejs instalirajte Node.js 22.12+ (preporuka: Node.js 24).'
  exit 1
fi
if [[ ! -d frontend/node_modules ]]; then
  npm --prefix frontend ci
fi
npm --prefix frontend run build
if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python -m src.web "$@"
else
  exec python3 -m src.web "$@"
fi

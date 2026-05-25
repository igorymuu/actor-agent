#!/bin/bash
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 2

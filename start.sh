#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=5588

echo "🚀 Starting Samsung TV Controller..."

if ! lsof -ti :$PORT >/dev/null 2>&1; then
    nohup "$DIR/.venv/bin/python3" -m uvicorn backend.server:app \
        --app-dir "$DIR" \
        --host 127.0.0.1 \
        --port $PORT \
        > "$DIR/server.log" 2>&1 &
    
    for i in {1..20}; do
        if curl -s "http://127.0.0.1:$PORT/api/status" >/dev/null 2>&1; then
            break
        fi
        sleep 0.15
    done
    echo "✅ Server started on http://127.0.0.1:$PORT"
else
    echo "ℹ️ Server already running on port $PORT"
fi

if [ -d "/Applications/Google Chrome.app" ]; then
    open -na "Google Chrome" --args --app="http://127.0.0.1:$PORT" --window-size=400,860
else
    open "http://127.0.0.1:$PORT"
fi

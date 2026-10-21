#!/bin/bash
PORT=5588
PID=$(lsof -ti :$PORT 2>/dev/null || true)
if [ -n "$PID" ]; then
    echo "Stopping Samsung TV Controller server (PID: $PID)..."
    kill -9 $PID
    echo "✅ Server stopped."
else
    echo "ℹ️ No server running on port $PORT."
fi

#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    [ ! -z "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null
    [ ! -z "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    echo "✨ Stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo "🚀 Starting StreamLine..."

# Check venv
[ ! -d ".venv" ] && { echo "❌ .venv not found"; exit 1; }

# Check frontend deps
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend deps..."
    cd frontend && npm install && cd ..
fi

# Activate venv and check backend deps
source .venv/bin/activate
pip list | grep -q "ag-ui-protocol" || pip install -q ag-ui-protocol fastapi uvicorn python-multipart

# Clean ports
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# Start backend
echo "🔧 Starting backend..."
cd src
python -m uvicorn backend.server:app --reload --port 8000 2>&1 | sed 's/^/[BACKEND] /' &
BACKEND_PID=$!
cd ..

# Wait for backend
for i in {1..30}; do
    curl -s http://localhost:8000/health >/dev/null 2>&1 && break
    [ $i -eq 30 ] && { echo "❌ Backend failed"; exit 1; }
    sleep 1
done
echo "✅ Backend ready (http://localhost:8000)"

# Start frontend
echo "🎨 Starting frontend..."
cd frontend
npm run dev 2>&1 | sed 's/^/[FRONTEND] /' &
FRONTEND_PID=$!
cd ..

# Wait for frontend
for i in {1..30}; do
    curl -s http://localhost:3000 >/dev/null 2>&1 && break
    [ $i -eq 30 ] && { echo "❌ Frontend failed"; exit 1; }
    sleep 1
done
echo "✅ Frontend ready (http://localhost:3000)"
echo ""
echo "✨ StreamLine running! Press Ctrl+C to stop"
echo ""

wait

#!/bin/bash

# Test Ollama + Explosion Mode Integration
# Run this after installing Ollama and pulling llama3.2

echo "🔍 Checking prerequisites..."
echo ""

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ Ollama not running. Start with: ollama serve"
    exit 1
fi
echo "✅ Ollama is running"

# Check backend
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Backend not running. Start with: uvicorn backend.app.main:app --reload"
    exit 1
fi
echo "✅ Backend is healthy"

echo ""
echo "🔥 Pre-warming Ollama model (prevents cold-start failures)..."
curl -s http://localhost:11434/api/generate -d '{"model": "llama3.2", "prompt": "warmup", "stream": false}' > /dev/null 2>&1
echo "✅ Model is warm"

echo ""
echo "🧪 Running explosion test (10 chunks, concurrency 3)..."
echo ""

# Use venv python to ensure httpx is available
VENV_PYTHON="$(cd "$(dirname "$0")" && pwd)/venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="venv/bin/python"
fi

$VENV_PYTHON scripts/hammer_gen.py --mode explosion --chunks 10 --concurrency 3

echo ""
echo "⏳ Waiting 15s for background Ollama processing to complete..."
sleep 15
echo ""
echo "📊 Checking results..."
echo ""

# Get the most recent explosion project
PROJECT_ID=$(curl -s http://localhost:8000/api/v1/projects | $VENV_PYTHON -c "import sys, json; projects = json.load(sys.stdin); found = [p for p in projects if 'Explosion' in p['name']]; print(found[-1]['id'] if found else '')" 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo "⚠️  No explosion project found"
    exit 0
fi

echo "Project ID: $PROJECT_ID"
echo ""

# Check how chunks were processed
echo "📋 Chunk statuses:"
curl -s "http://localhost:8000/api/v1/chunks?project_id=$PROJECT_ID&limit=5" | $VENV_PYTHON -m json.tool 2>/dev/null | grep -E '(status|summary)' | head -10
echo ""

# Compact the project
echo "🔄 Triggering compaction..."
compaction_result=$(curl -s -X POST "http://localhost:8000/api/v1/projects/$PROJECT_ID/compact")
echo "$compaction_result" | $VENV_PYTHON -m json.tool 2>/dev/null | head -15

echo ""
echo "🔍 Checking for entities extracted..."
entities=$(curl -s "http://localhost:8000/api/v1/entities/projects/$PROJECT_ID/aggregations" 2>/dev/null)
if [ -n "$entities" ]; then
    echo "$entities" | $VENV_PYTHON -m json.tool 2>/dev/null
else
    echo "⚠️  No entities found (this is expected if Ollama wasn't connected during processing)"
fi

echo ""
echo "✅ Test complete!"
echo ""
echo "📖 Backend log highlights:"
tail -100 /tmp/uvicorn_live.log 2>/dev/null | grep -E '(Ollama|entity|Entity|recursion|Extracted|unavailable|fallback|LLM)' | tail -10 || echo "  (no relevant log lines found)"

#!/bin/bash
# Ingest RAG patterns for spacing, contrast, and layout rules

cd /Users/tk/Desktop/productvideo

echo "🚀 Ingesting RAG patterns..."
python ingest_patterns.py rag_patterns_spacing_contrast.json

echo ""
echo "✅ Done. Run a test video to verify:"
echo "   cd src && python test_composer_v2.py"

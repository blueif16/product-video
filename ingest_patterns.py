#!/usr/bin/env python3
"""
Ingest RAG patterns from JSON file into Supabase knowledge base.

Usage:
    python ingest_patterns.py rag_patterns_spacing_contrast.json
    python ingest_patterns.py rag_patterns_spacing_contrast.json --namespace remotion_execution_patterns
"""
import sys
import json
import argparse
from pathlib import Path

# Add supa-langgraph-rag to path
rag_scaffold_path = Path(__file__).parent / "supa-langgraph-rag-scaffold" / "backend"
sys.path.insert(0, str(rag_scaffold_path))

from dotenv import load_dotenv
load_dotenv()

from app.core import RAGStore


def ingest_patterns(json_path: str, namespace_override: str = None):
    """Ingest patterns from JSON file."""
    
    with open(json_path) as f:
        data = json.load(f)
    
    namespace = namespace_override or data.get("namespace", "remotion_execution_patterns")
    patterns = data.get("patterns", [])
    
    if not patterns:
        print("❌ No patterns found in JSON")
        return
    
    print(f"📚 Ingesting {len(patterns)} patterns into '{namespace}'...")
    
    rag = RAGStore(namespace=namespace)
    
    # Convert to batch format
    items = []
    for p in patterns:
        items.append({
            "content": p["content"],
            "source": p.get("metadata", {}).get("source", "manual"),
            "type": p.get("metadata", {}).get("type", "pattern")
        })
    
    result = rag.ingest_batch(items)
    
    print(f"✓ Created: {result['created']}")
    print(f"⏭ Skipped (duplicates): {result['skipped']}")
    
    # Show stats
    stats = rag.stats()
    print(f"📊 Total in '{namespace}': {stats['documents']} documents, {stats['relations']} relations")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest RAG patterns from JSON")
    parser.add_argument("json_file", help="Path to JSON file with patterns")
    parser.add_argument("--namespace", "-n", help="Override namespace from JSON")
    
    args = parser.parse_args()
    
    if not Path(args.json_file).exists():
        print(f"❌ File not found: {args.json_file}")
        sys.exit(1)
    
    ingest_patterns(args.json_file, args.namespace)

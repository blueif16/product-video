"""
Test RAG integration with composer
"""
import sys
sys.path.insert(0, "supa-langgraph-rag-scaffold/backend")

from app.core import RAGStore

# Test RAG query
rag = RAGStore(namespace="remotion_execution_patterns")

# Test query
query = "kinetic energy text animation timing"
print(f"Query: {query}\n")

results = rag.search(query, top_k=3)

print(f"Found {len(results)} patterns:\n")

for i, result in enumerate(results, 1):
    content = result.get("content", "")
    metadata = result.get("metadata", {})
    pattern_type = metadata.get("type", "unknown")

    print(f"Pattern {i} ({pattern_type}):")
    print(content[:200] + "...\n")

print("✓ RAG integration test successful")

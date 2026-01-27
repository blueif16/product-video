"""
RAG Tools for Composer

Query execution pattern knowledge base following supa-langgraph-rag approach.
"""
import sys
from pathlib import Path
from typing import Annotated
from langchain_core.tools import tool

# Add supa-langgraph-rag to path
rag_scaffold_path = Path(__file__).parent.parent.parent / "supa-langgraph-rag-scaffold" / "backend"
sys.path.insert(0, str(rag_scaffold_path))

from app.core import RAGStore


@tool
def query_execution_patterns(
    query: str,
    match_count: int = 3
) -> str:
    """
    Query the remotion execution pattern knowledge base.

    Use this when you need specific guidance on:
    - Energy execution techniques (kinetic, elegant, calm, bold, creative)
    - Layout patterns (vertical stack, horizontal split, centered hero)
    - Timing and temporal distribution strategies
    - Animation combinations and techniques
    - Spacing calculations and positioning formulas
    - Common mistakes to avoid (anti-patterns)

    Args:
        query: Natural language query describing what patterns you need.
               Examples:
               - "kinetic energy staggered text reveals"
               - "vertical stack layout with portrait image"
               - "text spacing calculation for stacked elements"
               - "5 second clip timing distribution"
        match_count: Number of patterns to retrieve (default 3, max 5)

    Returns:
        Formatted patterns with detailed execution guidance
    """
    try:
        print(f"   🔍 Querying knowledge base: {query[:60]}...")

        rag = RAGStore(namespace="remotion_execution_patterns")
        results = rag.search(query, top_k=min(match_count, 5))

        if not results:
            print(f"   ⚠️  No patterns found for query")
            return "No patterns found. Try a different query or proceed with your own knowledge."

        print(f"   ✓ Found {len(results)} execution patterns")

        sections = []
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            pattern_type = metadata.get("type", "pattern")

            sections.append(f"### Pattern {i} ({pattern_type})\n\n{content}")

        return "\n\n---\n\n".join(sections)

    except Exception as e:
        print(f"   ❌ RAG query failed: {str(e)}")
        return f"RAG query failed: {str(e)}. Proceed with your own knowledge."

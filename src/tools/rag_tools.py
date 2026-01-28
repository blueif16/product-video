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
    Query remotion execution pattern knowledge base for energy-specific techniques,
    layout patterns, timing strategies, and animation combinations.

    Args:
        query: Natural language query (e.g., "kinetic energy staggered text reveals")
        match_count: Number of patterns to retrieve (default 3, max 5)

    Returns:
        Formatted patterns with execution guidance
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


@tool
def query_video_planning_patterns(
    query: str,
    match_count: int = 3
) -> str:
    """
    Query video planning pattern knowledge base for high-level video structure,
    narrative arcs, rhythm design, clip functions, and overall pacing strategies.

    Args:
        query: Natural language query (e.g., "hook body cta structure for product demo")
        match_count: Number of patterns to retrieve (default 3, max 5)

    Returns:
        Formatted patterns with planning guidance
    """
    try:
        print(f"   🔍 Querying planning knowledge base: {query[:60]}...")

        rag = RAGStore(namespace="video_planning_patterns")
        results = rag.search(query, top_k=min(match_count, 5))

        if not results:
            print(f"   ⚠️  No planning patterns found for query")
            return "No planning patterns found. Try a different query or proceed with your own knowledge."

        print(f"   ✓ Found {len(results)} planning patterns")

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

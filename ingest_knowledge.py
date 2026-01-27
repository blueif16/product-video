#!/usr/bin/env python3
"""
RAG Knowledge Ingestion Script

Reads research findings from JSON and ingests into Supabase knowledge base.

Usage:
    python ingest_knowledge.py rag_research_template.json
    python ingest_knowledge.py my_patterns.json --namespace custom_patterns
"""
import json
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add backend directory to path to import app module
sys.path.insert(0, str(Path(__file__).parent / "supa-langgraph-rag-scaffold" / "backend"))

from app.core import RAGStore


def ingest_from_json(
    json_path: str,
    namespace_override: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """
    Ingest patterns from JSON file into knowledge base.
    
    Args:
        json_path: Path to JSON file with patterns
        namespace_override: Override namespace from JSON
        dry_run: If True, show what would be ingested without actually doing it
    
    Returns:
        Statistics about ingestion
    """
    # Load JSON
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    namespace = namespace_override or data.get("namespace", "remotion_execution_patterns")
    patterns = data.get("patterns", [])
    
    print(f"\n{'='*60}")
    print(f"RAG Knowledge Ingestion")
    print(f"{'='*60}")
    print(f"Source: {json_path}")
    print(f"Namespace: {namespace}")
    print(f"Patterns: {len(patterns)}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")
    
    if dry_run:
        print("Dry run - showing what would be ingested:\n")
        for i, pattern in enumerate(patterns, 1):
            print(f"{i}. {pattern['id']}")
            print(f"   Content length: {len(pattern['content'])} chars")
            print(f"   Metadata: {pattern.get('metadata', {})}")
            print(f"   Relations: {len(pattern.get('relations', []))}")
            print()
        return {
            "ingested": 0,
            "relations": 0,
            "dry_run": True,
        }
    
    # Initialize RAG store
    rag = RAGStore(namespace=namespace)
    
    # Track ID mapping (pattern.id -> database UUID)
    id_map = {}
    stats = {
        "ingested": 0,
        "relations": 0,
        "errors": [],
    }
    
    # Phase 1: Ingest all patterns
    print("Phase 1: Ingesting patterns...")
    for i, pattern in enumerate(patterns, 1):
        try:
            pattern_id = pattern["id"]
            content = pattern["content"]
            metadata = pattern.get("metadata", {})

            # Extract source and type from metadata
            source = metadata.get("source")
            type_value = metadata.get("type")

            # Ingest (RAGStore.ingest accepts source and type as separate params)
            result = rag.ingest(content, source=source, type=type_value)
            
            # Store mapping
            if result and "id" in result:
                id_map[pattern_id] = result["id"]
                stats["ingested"] += 1
                print(f"   ✓ [{i}/{len(patterns)}] {pattern_id}")
            else:
                stats["errors"].append(f"Failed to ingest {pattern_id}: No ID returned")
                print(f"   ✗ [{i}/{len(patterns)}] {pattern_id} - No ID returned")
        
        except Exception as e:
            stats["errors"].append(f"Error ingesting {pattern.get('id', 'unknown')}: {str(e)}")
            print(f"   ✗ [{i}/{len(patterns)}] {pattern.get('id', 'unknown')} - {e}")
    
    print(f"\n✓ Ingested {stats['ingested']}/{len(patterns)} patterns")
    
    # Phase 2: Create relationships
    print("\nPhase 2: Creating relationships...")
    for pattern in patterns:
        pattern_id = pattern["id"]
        
        if pattern_id not in id_map:
            continue  # Skip if pattern wasn't ingested
        
        from_uuid = id_map[pattern_id]
        relations = pattern.get("relations", [])
        
        for relation in relations:
            try:
                to_id = relation["to_id"]
                relation_type = relation["relation_type"]
                
                if to_id not in id_map:
                    stats["errors"].append(f"Relation target not found: {pattern_id} -> {to_id}")
                    continue
                
                to_uuid = id_map[to_id]
                
                # Add relation
                rag.add_relation(from_uuid, to_uuid, relation_type)
                stats["relations"] += 1
                print(f"   ✓ {pattern_id} --[{relation_type}]--> {to_id}")
            
            except Exception as e:
                stats["errors"].append(f"Error creating relation {pattern_id} -> {relation.get('to_id')}: {str(e)}")
                print(f"   ✗ {pattern_id} -> {relation.get('to_id')} - {e}")
    
    print(f"\n✓ Created {stats['relations']} relationships")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Ingestion Complete")
    print(f"{'='*60}")
    print(f"Patterns ingested: {stats['ingested']}/{len(patterns)}")
    print(f"Relations created: {stats['relations']}")
    print(f"Errors: {len(stats['errors'])}")
    
    if stats['errors']:
        print(f"\nErrors encountered:")
        for error in stats['errors']:
            print(f"  - {error}")
    
    print(f"{'='*60}\n")
    
    return stats


def test_search(namespace: str, query: str, match_count: int = 3):
    """
    Test searching the ingested knowledge.
    
    Args:
        namespace: Namespace to search
        query: Search query
        match_count: Number of results
    """
    print(f"\n{'='*60}")
    print(f"Testing Search")
    print(f"{'='*60}")
    print(f"Namespace: {namespace}")
    print(f"Query: {query}")
    print(f"Match count: {match_count}")
    print(f"{'='*60}\n")
    
    rag = RAGStore(namespace=namespace)
    results = rag.search_context_mesh(query, match_count=match_count)
    
    print(f"Found {len(results)} results:\n")
    
    for i, result in enumerate(results, 1):
        content_preview = result.get("content", "")[:200] + "..."
        metadata = result.get("metadata", {})
        pattern_id = metadata.get("pattern_id", "unknown")
        
        print(f"{i}. Pattern: {pattern_id}")
        print(f"   Preview: {content_preview}")
        print(f"   Metadata: {metadata}")
        print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Ingest RAG knowledge from JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest from template
  python ingest_knowledge.py rag_research_template.json
  
  # Dry run (preview)
  python ingest_knowledge.py my_patterns.json --dry-run
  
  # Override namespace
  python ingest_knowledge.py patterns.json --namespace my_custom_namespace
  
  # Ingest then test
  python ingest_knowledge.py patterns.json --test "kinetic energy text"
        """
    )
    
    parser.add_argument("json_file", help="Path to JSON file with patterns")
    parser.add_argument("--namespace", help="Override namespace from JSON")
    parser.add_argument("--dry-run", action="store_true", help="Preview without ingesting")
    parser.add_argument("--test", metavar="QUERY", help="Test search after ingestion")
    parser.add_argument("--match-count", type=int, default=3, help="Results for test query")
    
    args = parser.parse_args()
    
    # Validate file exists
    if not Path(args.json_file).exists():
        print(f"Error: File not found: {args.json_file}")
        sys.exit(1)
    
    # Ingest
    stats = ingest_from_json(
        args.json_file,
        namespace_override=args.namespace,
        dry_run=args.dry_run,
    )
    
    # Test search if requested
    if args.test and not args.dry_run:
        # Load namespace from JSON if not overridden
        with open(args.json_file, 'r') as f:
            data = json.load(f)
        namespace = args.namespace or data.get("namespace", "remotion_execution_patterns")
        
        test_search(namespace, args.test, args.match_count)
    
    # Exit code based on errors
    if stats.get("errors"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

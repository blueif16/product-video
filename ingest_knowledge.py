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


def list_namespaces() -> list[dict]:
    """
    List all available namespaces with their statistics.

    Returns:
        List of namespace info dicts
    """
    print(f"\n{'='*60}")
    print(f"Available Namespaces")
    print(f"{'='*60}\n")

    # Get all unique namespaces from documents table
    rag = RAGStore()
    result = rag.client.table("documents").select("namespace").execute()

    if not result.data:
        print("No namespaces found.")
        return []

    # Count documents and relations per namespace
    namespaces = {}
    for row in result.data:
        ns = row["namespace"]
        if ns not in namespaces:
            namespaces[ns] = {"namespace": ns, "documents": 0, "relations": 0}
        namespaces[ns]["documents"] += 1

    # Get relations count
    rel_result = rag.client.table("doc_relations").select("namespace").execute()
    for row in rel_result.data:
        ns = row["namespace"]
        if ns in namespaces:
            namespaces[ns]["relations"] += 1

    # Display
    namespace_list = sorted(namespaces.values(), key=lambda x: x["namespace"])
    for ns_info in namespace_list:
        print(f"  {ns_info['namespace']}")
        print(f"    Documents: {ns_info['documents']}")
        print(f"    Relations: {ns_info['relations']}")
        print()

    print(f"Total: {len(namespace_list)} namespace(s)")
    print(f"{'='*60}\n")

    return namespace_list


def clear_namespace(namespace: str, confirm: bool = True) -> dict:
    """
    Clear all data in a namespace.

    This will delete:
    - All documents in the namespace
    - All graph relations (doc_relations) in the namespace

    Args:
        namespace: Namespace to clear
        confirm: Require confirmation before clearing

    Returns:
        Statistics about deletion
    """
    print(f"\n{'='*60}")
    print(f"Clear Namespace")
    print(f"{'='*60}")
    print(f"Namespace: {namespace}")
    print(f"{'='*60}\n")

    # Show current stats
    rag = RAGStore(namespace=namespace)
    stats = rag.stats()

    print(f"Current state:")
    print(f"  Documents: {stats['documents']}")
    print(f"  Relations: {stats['relations']}")
    print()

    if stats['documents'] == 0 and stats['relations'] == 0:
        print("Namespace is already empty.")
        return {"deleted": 0}

    # Confirm
    if confirm:
        response = input(f"Are you sure you want to delete ALL data in '{namespace}'? (yes/no): ")
        if response.lower() != "yes":
            print("Cancelled.")
            return {"deleted": 0, "cancelled": True}

    # Delete
    print("\nDeleting...")
    result = rag.delete_all()

    print(f"\n✓ Deleted {result['deleted']} documents and all relations")
    print(f"{'='*60}\n")

    return result


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest RAG knowledge from JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest from template
  python ingest_knowledge.py assets/knowledge/v2.json
  python ingest_knowledge.py assets/knowledge/v2_gemini.json


  # Dry run (preview)
  python ingest_knowledge.py my_patterns.json --dry-run

  # Override namespace
  python ingest_knowledge.py patterns.json --namespace my_custom_namespace

  # Ingest then test
  python ingest_knowledge.py patterns.json --test "kinetic energy text"

  # Clear namespace
  python ingest_knowledge.py --clear --namespace remotion_execution_patterns

  # Clear without confirmation (dangerous!)
  python ingest_knowledge.py --clear --namespace test_data --yes

  # List all namespaces
  python ingest_knowledge.py --list
        """
    )

    parser.add_argument("json_file", nargs="?", help="Path to JSON file with patterns")
    parser.add_argument("--namespace", help="Override namespace from JSON")
    parser.add_argument("--dry-run", action="store_true", help="Preview without ingesting")
    parser.add_argument("--test", metavar="QUERY", help="Test search after ingestion")
    parser.add_argument("--match-count", type=int, default=3, help="Results for test query")
    parser.add_argument("--list", action="store_true", help="List all namespaces")
    parser.add_argument("--clear", action="store_true", help="Clear all data in namespace")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation for --clear")
    
    args = parser.parse_args()

    # Handle list mode
    if args.list:
        list_namespaces()
        sys.exit(0)

    # Handle clear mode
    if args.clear:
        if not args.namespace:
            print("Error: --namespace is required when using --clear")
            sys.exit(1)
        clear_namespace(args.namespace, confirm=not args.yes)
        sys.exit(0)

    # Validate file exists for ingest mode
    if not args.json_file:
        print("Error: json_file is required (or use --clear)")
        parser.print_help()
        sys.exit(1)

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

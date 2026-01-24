#!/usr/bin/env python3
"""
Editor V2 Validation Script

Checks for common issues after migration:
- Import errors
- Database schema compatibility
- Tool function availability
- State structure consistency
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def check_imports():
    """Check all imports work correctly."""
    print("\n🔍 Checking imports...")
    issues = []
    
    try:
        from editor import graph
        print("   ✓ editor.graph")
    except ImportError as e:
        issues.append(f"editor.graph: {e}")
    
    try:
        from editor import planner
        print("   ✓ editor.planner")
    except ImportError as e:
        issues.append(f"editor.planner: {e}")
    
    try:
        from editor import clip_composer
        print("   ✓ editor.clip_composer")
    except ImportError as e:
        issues.append(f"editor.clip_composer: {e}")
    
    try:
        from editor import assembler
        print("   ✓ editor.assembler")
    except ImportError as e:
        issues.append(f"editor.assembler: {e}")
    
    try:
        from editor import state
        print("   ✓ editor.state")
    except ImportError as e:
        issues.append(f"editor.state: {e}")
    
    try:
        from editor import loader
        print("   ✓ editor.loader")
    except ImportError as e:
        issues.append(f"editor.loader: {e}")
    
    try:
        from tools import editor_tools
        print("   ✓ tools.editor_tools")
    except ImportError as e:
        issues.append(f"tools.editor_tools: {e}")
    
    return issues


def check_state_structure():
    """Verify EditorState has required fields."""
    print("\n🔍 Checking state structure...")
    issues = []
    
    try:
        from editor.state import EditorState
        
        # Create a test state to check all fields exist
        test_state = EditorState(
            video_project_id="test",
            user_input="test",
            analysis_summary="test",
            assets=[],
            edit_plan_summary=None,
            clip_task_ids=[],
            clip_specs=[],
            generated_asset_ids=[],
            pending_clip_task_ids=None,
            current_clip_index=None,
            video_spec=None,
            video_spec_id=None,
            music_analysis=None,
            composition_plan=None,
            refined_composition_plan=None,
            audio_path=None,
            render_status=None,
            render_path=None,
            render_error=None,
            final_video_path=None,
            mux_error=None,
            style_guide=None,  # V2 addition
        )
        
        print("   ✓ EditorState structure")
        
        # Check if style_guide field exists (TypedDict is a dict at runtime)
        if "style_guide" in test_state:
            print("   ✓ style_guide field present")
        else:
            issues.append("EditorState missing style_guide field")
            
    except Exception as e:
        issues.append(f"EditorState check failed: {e}")
    
    return issues


def check_tool_functions():
    """Verify all tool functions exist and are properly decorated."""
    print("\n🔍 Checking tool functions...")
    issues = []
    
    try:
        from tools.editor_tools import (
            create_clip_task,
            finalize_edit_plan,
            generate_enhanced_image,
            submit_clip_spec,
        )
        
        # Check they're decorated as tools
        if hasattr(create_clip_task, 'name'):
            print("   ✓ create_clip_task")
        else:
            issues.append("create_clip_task not decorated as @tool")
        
        if hasattr(finalize_edit_plan, 'name'):
            print("   ✓ finalize_edit_plan")
        else:
            issues.append("finalize_edit_plan not decorated as @tool")
        
        if hasattr(generate_enhanced_image, 'name'):
            print("   ✓ generate_enhanced_image")
        else:
            issues.append("generate_enhanced_image not decorated as @tool")
        
        if hasattr(submit_clip_spec, 'name'):
            print("   ✓ submit_clip_spec")
        else:
            issues.append("submit_clip_spec not decorated as @tool")
            
    except Exception as e:
        issues.append(f"Tool function check failed: {e}")
    
    return issues


def check_node_functions():
    """Verify all node functions exist."""
    print("\n🔍 Checking node functions...")
    issues = []
    
    try:
        from editor.planner import edit_planner_node
        print("   ✓ edit_planner_node")
    except Exception as e:
        issues.append(f"edit_planner_node: {e}")
    
    try:
        from editor.clip_composer import compose_all_clips_node, compose_single_clip_node
        print("   ✓ compose_all_clips_node")
        print("   ✓ compose_single_clip_node")
    except Exception as e:
        issues.append(f"compose nodes: {e}")
    
    try:
        from editor.assembler import edit_assembler_node
        print("   ✓ edit_assembler_node")
    except Exception as e:
        issues.append(f"edit_assembler_node: {e}")
    
    return issues


def check_database_schema():
    """Verify database tables exist with correct columns."""
    print("\n🔍 Checking database schema...")
    issues = []
    
    try:
        from db.supabase_client import get_client
        client = get_client()
        
        # Check video_projects table
        try:
            result = client.table("video_projects").select("*").limit(1).execute()
            print("   ✓ video_projects table exists")
        except Exception as e:
            issues.append(f"video_projects table: {e}")
        
        # Check clip_tasks table
        try:
            result = client.table("clip_tasks").select("*").limit(1).execute()
            print("   ✓ clip_tasks table exists")
        except Exception as e:
            issues.append(f"clip_tasks table: {e}")
        
        # Check video_specs table
        try:
            result = client.table("video_specs").select("*").limit(1).execute()
            print("   ✓ video_specs table exists")
        except Exception as e:
            issues.append(f"video_specs table: {e}")
        
        # Check generated_assets table
        try:
            result = client.table("generated_assets").select("*").limit(1).execute()
            print("   ✓ generated_assets table exists")
        except Exception as e:
            issues.append(f"generated_assets table: {e}")
            
    except Exception as e:
        issues.append(f"Database connection failed: {e}")
    
    return issues


def check_graph_build():
    """Try to build the graph."""
    print("\n🔍 Checking graph build...")
    issues = []
    
    try:
        from editor.graph import build_editor_graph
        
        graph = build_editor_graph(
            use_parallel_composition=False,
            include_render=False,
            include_music=False,
        )
        
        print("   ✓ Graph builds successfully")
        
        # Try to get nodes
        if hasattr(graph, 'nodes'):
            node_names = list(graph.nodes.keys())
            print(f"   ✓ Graph has {len(node_names)} nodes: {', '.join(node_names)}")
        
    except Exception as e:
        issues.append(f"Graph build failed: {e}")
        import traceback
        traceback.print_exc()
    
    return issues


def check_test_mode():
    """Try running in test mode."""
    print("\n🔍 Checking test mode...")
    issues = []
    
    try:
        from editor.loader import create_test_state
        from editor.graph import build_editor_graph
        
        # Create test state
        state = create_test_state()
        print("   ✓ Test state created")
        
        # Try to build graph
        graph = build_editor_graph(
            use_parallel_composition=False,
            include_render=False,
            include_music=False,
        )
        
        print("   ✓ Test mode ready")
        print("   ℹ️  Run: python -m editor.graph to test full execution")
        
    except Exception as e:
        issues.append(f"Test mode check failed: {e}")
        import traceback
        traceback.print_exc()
    
    return issues


def main():
    """Run all validation checks."""
    print("="*60)
    print("Editor V2 Validation")
    print("="*60)
    
    all_issues = []
    
    all_issues.extend(check_imports())
    all_issues.extend(check_state_structure())
    all_issues.extend(check_tool_functions())
    all_issues.extend(check_node_functions())
    all_issues.extend(check_database_schema())
    all_issues.extend(check_graph_build())
    all_issues.extend(check_test_mode())
    
    print("\n" + "="*60)
    if all_issues:
        print(f"❌ Found {len(all_issues)} issues:")
        for i, issue in enumerate(all_issues, 1):
            print(f"\n{i}. {issue}")
        print("\n" + "="*60)
        return 1
    else:
        print("✅ All checks passed!")
        print("\nYou're ready to run the editor:")
        print("  1. Clean DB: python -m src.editor.restart_editor PROJECT_ID --cleanup")
        print("  2. Run editor: python -m src.editor.graph")
        print("  3. Or from Python:")
        print("     from editor.graph import run_editor_standalone")
        print("     result = run_editor_standalone('your-project-id')")
        print("\n" + "="*60)
        return 0


if __name__ == "__main__":
    sys.exit(main())

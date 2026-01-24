"""
Aggregate node: Collect results, update status to 'aggregated'.
"""
from langchain_core.messages import AIMessage

from config import Config
from db.supabase_client import get_supabase, update_video_project_status
from .state import PipelineState
from .session import get_session


def aggregate_node(state: PipelineState) -> dict:
    """Aggregate capture results and update project status."""
    session = get_session()
    session.current_stage = "aggregating"
    
    video_project_id = state.get("video_project_id")
    if not video_project_id:
        print("WARNING: No video_project_id, cannot aggregate")
        return {"messages": [AIMessage(content="No project ID for aggregation")]}
    
    # Query tasks for THIS project only (not all tasks for the app)
    db = get_supabase()
    all_tasks = db.table("capture_tasks").select("*").eq(
        "video_project_id", video_project_id
    ).execute().data
    
    successful = [t for t in all_tasks if t["status"] == "success"]
    failed = [t for t in all_tasks if t["status"] == "failed"]
    
    # Update status
    update_video_project_status(video_project_id, "aggregated")
    
    print(f"\n{'=' * 60}")
    print(f"RESULTS: {len(successful)} success, {len(failed)} failed")
    print(f"{'=' * 60}")
    
    if failed:
        print(f"\nFailed:")
        for t in failed[:5]:
            notes = t.get('validation_notes', '')[:50] if t.get('validation_notes') else 'No notes'
            print(f"  - {t['id'][:8]}... : {notes}")
    
    if successful:
        print(f"\n✅ {len(successful)} assets ready at {Config.CAPTURES_OUTPUT_DIR}")
    else:
        print(f"\n❌ No assets captured")
    
    print(f"{'=' * 60}\n")
    
    return {
        "messages": [AIMessage(content=f"Aggregated: {len(successful)} success, {len(failed)} failed")]
    }

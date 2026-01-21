"""
Aggregate node: Collect results, update status to 'aggregated'.
"""
from langchain_core.messages import AIMessage

from config import Config
from db.supabase_client import get_all_tasks, update_video_project_status
from .state import PipelineState
from .session import get_session


def aggregate_node(state: PipelineState) -> dict:
    """Aggregate capture results and update project status."""
    session = get_session()
    session.current_stage = "aggregating"
    
    app_bundle_id = state.get("app_bundle_id", "com.app.unknown")
    
    all_tasks = get_all_tasks(app_bundle_id)
    successful = [t for t in all_tasks if t["status"] == "success"]
    failed = [t for t in all_tasks if t["status"] == "failed"]
    
    # Update status
    if state.get("video_project_id"):
        update_video_project_status(state["video_project_id"], "aggregated")
    
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

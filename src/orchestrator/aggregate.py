"""
Aggregate node: Collect results, copy assets to Remotion public directory, update status.

Now also extracts visual design info from validation notes to inform the editor phase.
"""
from langchain_core.messages import AIMessage, HumanMessage
import shutil
import re
from pathlib import Path

from config import Config, get_model
from db.supabase_client import get_supabase, update_video_project_status
from .state import PipelineState
from .session import get_session


def extract_visual_design_from_notes(validation_notes: list[str]) -> str:
    """
    Extract visual design section from validation notes.
    Returns concatenated visual design observations.
    """
    visual_sections = []
    
    for notes in validation_notes:
        if not notes:
            continue
        
        # Look for VISUAL DESIGN section
        if "VISUAL DESIGN" in notes:
            # Extract from "VISUAL DESIGN" to "VERDICT" or end
            start = notes.find("VISUAL DESIGN")
            end = notes.find("VERDICT", start)
            if end == -1:
                end = len(notes)
            section = notes[start:end].strip()
            if section:
                visual_sections.append(section)
    
    return "\n\n".join(visual_sections)


def summarize_visual_design(visual_observations: str) -> str:
    """
    Use LLM to summarize visual design observations into a description of the app's appearance.
    Does NOT suggest video colors - just describes what the app looks like.
    """
    if not visual_observations or len(visual_observations.strip()) < 20:
        return ""
    
    model = get_model()
    
    prompt = f"""Based on these visual observations from app screenshots, write a CONCISE factual description of the app's appearance (3-5 lines max).

OBSERVATIONS:
{visual_observations}

Describe ONLY what you observe:
- Theme (light/dark)
- Background colors (include hex values)
- Text colors (include hex values)  
- Accent colors (include hex values)
- UI style (minimal, playful, technical, etc.)

Just factual observations. No recommendations.

Example: "Light theme. Cream backgrounds (#F5F2ED). Dark charcoal text (#1A1A1A). Soft blue accents (#5B9BD5) for charts and icons. Minimal, airy UI with rounded cards and generous whitespace."

Description:"""

    try:
        response = model.invoke([HumanMessage(content=prompt)])
        content = response.content
        
        # Handle list response from Gemini
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            content = "\n".join(text_parts)
        
        return content.strip() if content else ""
    except Exception as e:
        print(f"   ⚠️  Could not summarize visual design: {e}")
        return ""


def aggregate_node(state: PipelineState) -> dict:
    """
    Aggregate capture results and prepare assets for Remotion.
    
    Critical steps:
    1. Query tasks for THIS project only (not all tasks for the app)
    2. Copy successful screenshots to remotion/public/captures/<project_id>/
    3. Extract visual design info from validation notes
    4. Update analysis_summary with visual design
    5. Update database with Remotion-accessible paths (relative to public/)
    6. Update project status to 'aggregated'
    """
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
    
    print(f"\n{'=' * 60}")
    print(f"RESULTS: {len(successful)} success, {len(failed)} failed")
    print(f"{'=' * 60}")
    
    if failed:
        print(f"\nFailed:")
        for t in failed[:5]:
            notes = t.get('validation_notes', '')[:50] if t.get('validation_notes') else 'No notes'
            print(f"  - {t['id'][:8]}... : {notes}")
    
    # ═══════════════════════════════════════════════════════════════
    # EXTRACT VISUAL DESIGN FROM VALIDATION NOTES
    # ═══════════════════════════════════════════════════════════════
    visual_design_summary = ""
    if successful:
        print(f"\n🎨 Extracting visual design from validation notes...")
        
        validation_notes = [t.get("validation_notes", "") for t in successful]
        visual_observations = extract_visual_design_from_notes(validation_notes)
        
        if visual_observations:
            visual_design_summary = summarize_visual_design(visual_observations)
            if visual_design_summary:
                print(f"   ✓ Visual design extracted")
            else:
                print(f"   ⚠️  Could not summarize visual design")
        else:
            print(f"   ⚠️  No visual design sections found in validation notes")
    
    # ═══════════════════════════════════════════════════════════════
    # COPY ASSETS TO REMOTION PUBLIC DIRECTORY
    # ═══════════════════════════════════════════════════════════════
    if successful:
        print(f"\n📦 Copying {len(successful)} assets to Remotion public directory...")
        
        # Remotion expects assets in remotion/public/
        remotion_public_dir = Config.PROJECT_ROOT / "remotion" / "public" / "assets" / video_project_id
        remotion_public_dir.mkdir(parents=True, exist_ok=True)
        
        copied_count = 0
        for task in successful:
            old_path_str = task.get("asset_path")
            if not old_path_str:
                print(f"   ⚠️  Task {task['id'][:8]} has no asset_path, skipping")
                continue
            
            old_path = Path(old_path_str)
            if not old_path.exists():
                print(f"   ⚠️  File not found: {old_path}, skipping")
                continue
            
            # Copy to Remotion public directory
            new_path = remotion_public_dir / old_path.name
            
            # Store path RELATIVE to remotion/public/ for Remotion to access
            # Example: assets/09985d31-ece3-4528-9254-196959060070/weather_screen.png
            relative_path = f"assets/{video_project_id}/{old_path.name}"
            
            try:
                shutil.copy2(old_path, new_path)
                
                # Update database with Remotion-accessible path
                db.table("capture_tasks").update({
                    "asset_path": relative_path,  # Store relative path for Remotion
                    "updated_at": "now()"
                }).eq("id", task["id"]).execute()
                
                copied_count += 1
                print(f"   ✓ {old_path.name} → {relative_path}")
                
            except Exception as e:
                print(f"   ✗ Failed to copy {old_path.name}: {e}")
        
        print(f"\n✅ {copied_count} assets ready for Remotion at {remotion_public_dir}")
    else:
        print(f"\n❌ No assets captured")
    
    # ═══════════════════════════════════════════════════════════════
    # UPDATE ANALYSIS SUMMARY WITH VISUAL DESIGN
    # ═══════════════════════════════════════════════════════════════
    if visual_design_summary:
        print(f"\n📝 Updating analysis summary with visual design...")
        
        # Get current analysis summary
        project = db.table("video_projects").select("analysis_summary").eq(
            "id", video_project_id
        ).single().execute().data
        
        current_summary = project.get("analysis_summary", "") if project else ""
        
        # Append visual design section
        updated_summary = current_summary.strip()
        if updated_summary:
            updated_summary += "\n\n### Visual Design (from captured screenshots)\n"
        else:
            updated_summary = "### Visual Design (from captured screenshots)\n"
        updated_summary += visual_design_summary
        
        # Save back to DB
        db.table("video_projects").update({
            "analysis_summary": updated_summary,
            "updated_at": "now()"
        }).eq("id", video_project_id).execute()
        
        print(f"   ✓ Analysis summary updated with visual design")
    
    # Update project status
    update_video_project_status(video_project_id, "aggregated")
    
    print(f"{'=' * 60}\n")
    
    return {
        "messages": [AIMessage(content=f"Aggregated: {len(successful)} success, {len(failed)} failed, assets copied to Remotion")]
    }

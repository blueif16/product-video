"""
FastAPI server with AG-UI endpoints.

Run:
    cd /Users/tk/Desktop/productvideo
    python -m uvicorn ag_ui.server:app --reload --port 8000
    
Or from src:
    python -m uvicorn src.ag_ui.server:app --reload --port 8000
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Literal
import uuid
import tempfile
import os

from ag_ui.core import RunAgentInput
from .adapter import run_pipeline_stream, SSE_CONTENT_TYPE, get_capture_tasks_for_project


app = FastAPI(
    title="StreamLine AG-UI Server",
    description="AG-UI compatible API for video production pipeline",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# AG-UI Endpoint
# ─────────────────────────────────────────────────────────────

@app.post("/pipeline")
async def pipeline_endpoint(input_data: RunAgentInput):
    """
    Main AG-UI endpoint for pipeline execution.
    
    Streams AG-UI events as SSE.
    """
    # Extract mode from state if present
    mode = "full"
    include_render = True
    include_music = True
    
    if input_data.state:
        mode = input_data.state.get("pipeline_mode", "full")
        include_render = input_data.state.get("include_render", True)
        include_music = input_data.state.get("include_music", True)
    
    return StreamingResponse(
        run_pipeline_stream(
            input_data,
            mode=mode,
            include_render=include_render,
            include_music=include_music,
        ),
        media_type=SSE_CONTENT_TYPE,
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
        },
    )


# ─────────────────────────────────────────────────────────────
# REST Endpoints (for frontend data fetching)
# ─────────────────────────────────────────────────────────────

@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    from db.supabase_client import get_supabase

    supabase = get_supabase()
    result = supabase.table("video_projects") \
        .select("*") \
        .eq("id", project_id) \
        .single() \
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return result.data


@app.get("/projects/{project_id}/captures")
async def get_captures(project_id: str):
    """Get capture tasks for a project."""
    tasks = get_capture_tasks_for_project(project_id)
    return {"captures": tasks}


# ─────────────────────────────────────────────────────────────
# Upload Mode Endpoints
# ─────────────────────────────────────────────────────────────

class UploadProjectRequest(BaseModel):
    """Request to create project from uploads."""
    user_input: str
    assets: list[dict]  # [{filename, url, description}]


@app.post("/projects/from-uploads")
async def create_project_from_uploads(request: UploadProjectRequest):
    """
    Create a video project from uploaded assets.

    Returns project_id to use with editor-only mode.
    """
    from db.supabase_client import get_supabase

    supabase = get_supabase()
    
    # Create project
    project_id = str(uuid.uuid4())
    
    supabase.table("video_projects").insert({
        "id": project_id,
        "user_input": request.user_input,
        "status": "aggregated",  # Ready for editor
        "source": "upload",
        "pipeline_mode": "upload",
    }).execute()
    
    # Create capture tasks for each asset
    for i, asset in enumerate(request.assets):
        supabase.table("capture_tasks").insert({
            "id": str(uuid.uuid4()),
            "video_project_id": project_id,
            "task_description": asset.get("description", f"Uploaded asset {i+1}"),
            "capture_type": "screenshot",
            "asset_url": asset["url"],
            "status": "success",
        }).execute()
    
    return {
        "project_id": project_id,
        "asset_count": len(request.assets),
    }


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    description: str = Form(""),
):
    """
    Upload a single file to Supabase Storage with AI-powered image analysis.

    Used by upload-only mode to prepare assets before pipeline.
    Analyzes the image content using Gemini Vision to extract detailed descriptions.
    User's description is passed as context to guide the AI analysis.
    """
    from tools.storage import upload_asset
    from tools.image_analyzer import analyze_image

    # Save to temp file
    suffix = os.path.splitext(file.filename or ".png")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Analyze image with Gemini Vision, passing user's description as context
        print(f"🔍 Analyzing image: {file.filename}")
        if description:
            print(f"   📝 User note: {description}")
        
        analysis = analyze_image(tmp_path, user_note=description)

        # Use AI-generated description if available, fallback to user description or filename
        final_description = analysis.get("description")
        if not final_description or "error" in analysis:
            # Fallback to user-provided description or filename
            fallback = description or file.filename or "Uploaded image"
            final_description = f"Image file (portrait): {fallback}"
            print(f"⚠️  Analysis failed, using fallback: {final_description}")
        else:
            print(f"✓ Analysis complete: {final_description[:100]}...")

        # Upload to Supabase with a temp project ID
        url = upload_asset(
            tmp_path,
            project_id="uploads",
            subfolder="pending",
        )

        return {
            "url": url,
            "filename": file.filename,
            "description": final_description,
            "width": analysis.get("width", 0),
            "height": analysis.get("height", 0),
        }
    finally:
        os.unlink(tmp_path)


class BatchUploadRequest(BaseModel):
    """Request for batch upload with analysis."""
    files_data: list[dict]  # [{filename, data_url, description}]


@app.post("/upload-batch")
async def upload_batch(
    files: list[UploadFile] = File(...),
    descriptions: str = Form(""),  # JSON string of descriptions
):
    """
    Upload multiple files and analyze them in a single batch.
    
    Uses Gemini batch analysis to understand relationships between images.
    Faster than individual uploads when you have all files at once.
    
    Args:
        files: List of image files
        descriptions: JSON string of user notes, e.g. '["Dashboard", "Settings", ""]'
    """
    import json
    from tools.storage import upload_asset
    from tools.image_analyzer import analyze_image_batch
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Parse user notes
    try:
        user_notes = json.loads(descriptions) if descriptions else []
    except json.JSONDecodeError:
        user_notes = []
    
    # Ensure notes match files count
    if len(user_notes) != len(files):
        user_notes = user_notes + [""] * (len(files) - len(user_notes))
    
    # Save all files to temp
    temp_paths = []
    filenames = []
    
    try:
        for file in files:
            suffix = os.path.splitext(file.filename or ".png")[1]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            content = await file.read()
            tmp.write(content)
            tmp.close()
            temp_paths.append(tmp.name)
            filenames.append(file.filename)
        
        # Batch analyze with user notes
        print(f"🔍 Batch analyzing {len(temp_paths)} images...")
        analyses = analyze_image_batch(temp_paths, user_notes=user_notes)
        
        # Upload all files
        results = []
        for analysis, filename, temp_path in zip(analyses, filenames, temp_paths):
            url = upload_asset(
                temp_path,
                project_id="uploads",
                subfolder="pending",
            )
            
            results.append({
                "url": url,
                "filename": filename,
                "description": analysis.get("description", f"Image file (portrait): {filename}"),
                "width": analysis.get("width", 0),
                "height": analysis.get("height", 0),
            })
            
            print(f"✓ {filename}: {analysis.get('description', '')[:80]}...")
        
        return {
            "uploads": results,
            "total": len(results),
        }
    
    finally:
        # Cleanup temp files
        for path in temp_paths:
            try:
                os.unlink(path)
            except:
                pass


# ─────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "streamline-ag-ui",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "StreamLine AG-UI Server",
        "version": "1.0.0",
        "endpoints": {
            "pipeline": "POST /pipeline - AG-UI streaming endpoint",
            "project": "GET /projects/{id} - Get project details",
            "captures": "GET /projects/{id}/captures - Get capture tasks",
            "upload": "POST /upload - Upload single file with analysis",
            "upload_batch": "POST /upload-batch - Upload multiple files with batch analysis",
            "from_uploads": "POST /projects/from-uploads - Create project from uploads",
            "health": "GET /health - Health check",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

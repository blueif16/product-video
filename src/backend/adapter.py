"""
AG-UI Adapter for StreamLine Pipeline

Exposes the unified LangGraph pipeline via AG-UI protocol.
"""
import uuid
import asyncio
import time
from typing import AsyncGenerator, Optional

from ag_ui.core import (
    RunAgentInput,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    StateSnapshotEvent,
    StateDeltaEvent,
    CustomEvent,
)
from ag_ui.encoder import EventEncoder
from langgraph.types import Command

from pipeline.unified_graph import compile_unified_graph
from pipeline.state import create_initial_state
from .event_translator import EventTranslator, extract_ui_state, make_json_safe


SSE_CONTENT_TYPE = "text/event-stream"


def get_capture_tasks_for_project(project_id: str) -> list[dict]:
    """
    Fetch capture tasks with cloud URLs for frontend display.
    """
    if not project_id:
        return []

    try:
        from db.supabase_client import get_supabase

        supabase = get_supabase()
        result = supabase.table("capture_tasks") \
            .select("id, task_description, status, asset_url, capture_type") \
            .eq("video_project_id", project_id) \
            .execute()
        
        return [
            {
                "id": task["id"],
                "description": task.get("task_description", ""),
                "status": task.get("status", "pending"),
                "asset_url": task.get("asset_url"),
                "capture_type": task.get("capture_type", "screenshot"),
            }
            for task in result.data
        ]
    except Exception as e:
        print(f"Error fetching capture tasks: {e}")
        return []


async def run_pipeline_stream(
    input_data: RunAgentInput,
    mode: str = "full",
    include_render: bool = True,
    include_music: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Stream AG-UI events from pipeline execution with heartbeat keep-alive.

    Args:
        input_data: AG-UI input (messages, thread_id, run_id, state)
        mode: "full" | "editor_only" | "upload"
        include_render: Whether to render video
        include_music: Whether to generate music

    Yields:
        SSE-formatted AG-UI events
    """
    print(f"\n🚀 [PIPELINE] Starting pipeline stream - mode={mode}, render={include_render}, music={include_music}", flush=True)

    encoder = EventEncoder(accept=SSE_CONTENT_TYPE)
    thread_id = input_data.thread_id or str(uuid.uuid4())
    run_id = input_data.run_id or str(uuid.uuid4())

    print(f"📋 [PIPELINE] thread_id={thread_id[:8]}, run_id={run_id[:8]}", flush=True)

    translator = EventTranslator(thread_id, run_id)

    # 心跳追踪
    last_event_time = time.time()
    HEARTBEAT_INTERVAL = 15  # 秒
    
    # ─────────────────────────────────────────────────────────
    # 1. RUN_STARTED
    # ─────────────────────────────────────────────────────────
    print(f"  🔊 AG-UI: RUN_STARTED", flush=True)
    yield encoder.encode(RunStartedEvent(
        type=EventType.RUN_STARTED,
        thread_id=thread_id,
        run_id=run_id,
    ))
    last_event_time = time.time()
    await asyncio.sleep(0)  # Allow event loop to send data
    
    # ─────────────────────────────────────────────────────────
    # 2. Initial STATE_SNAPSHOT
    # ─────────────────────────────────────────────────────────
    
    # Extract user message
    user_message = ""
    for msg in input_data.messages:
        if msg.role == "user":
            user_message = msg.content
            break
    
    # Check for existing project ID in input state
    video_project_id = None
    if input_data.state:
        video_project_id = input_data.state.get("video_project_id")
        # Also check for mode override
        if "pipeline_mode" in input_data.state:
            mode = input_data.state["pipeline_mode"]

    print(f"📦 [PIPELINE] video_project_id={video_project_id}, user_message={user_message[:50] if user_message else 'None'}...", flush=True)
    
    initial_ui_state = {
        "pipeline_mode": mode,
        "status": "starting",
        "current_stage": "initializing",
        "stage_message": "Starting pipeline...",
        "progress_percent": 0,
        "video_project_id": video_project_id,
        "captures_total": 0,
        "captures_completed": 0,
        "capture_tasks": [],
    }

    print(f"  🔊 AG-UI: STATE_SNAPSHOT (initial)", flush=True)
    yield encoder.encode(StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot=initial_ui_state,
    ))
    last_event_time = time.time()
    await asyncio.sleep(0)  # Allow event loop to send data
    
    # ─────────────────────────────────────────────────────────
    # 3. Compile Graph
    # ─────────────────────────────────────────────────────────
    print(f"🔧 [PIPELINE] Compiling graph...", flush=True)
    graph = compile_unified_graph(
        include_render=include_render,
        include_music=include_music,
    )

    print(f"🎬 [PIPELINE] Creating initial state...", flush=True)
    initial_state = create_initial_state(
        user_input=user_message,
        mode=mode,
        video_project_id=video_project_id,
    )

    print(f"▶️  [PIPELINE] Starting graph execution...", flush=True)
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # ─────────────────────────────────────────────────────────
    # 4. Stream Graph Execution
    # ─────────────────────────────────────────────────────────
    last_project_id = video_project_id

    try:
        # Check if resuming from interrupt
        if hasattr(input_data, 'resume') and input_data.resume:
            resume_payload = input_data.resume.get("payload") if isinstance(input_data.resume, dict) else None

            # Resume graph with user's response
            async for event in graph.astream_events(
                Command(resume=resume_payload),
                config=config,
                version="v2",
            ):
                # Get current state if possible
                current_state = {}
                try:
                    state_snapshot = graph.get_state(config)
                    if state_snapshot and hasattr(state_snapshot, 'values'):
                        current_state = state_snapshot.values
                except:
                    pass

                # Translate LangGraph event to AG-UI events
                for ag_event in translator.translate(event, current_state):
                    print(f"  🔊 AG-UI: {ag_event.type} | {getattr(ag_event, 'step_name', '')} | {getattr(ag_event, 'delta', '')[:100] if hasattr(ag_event, 'delta') else ''}", flush=True)
                    yield encoder.encode(ag_event)
                    last_event_time = time.time()

                # Check for project ID updates
                if current_state:
                    new_project_id = current_state.get("video_project_id")
                    if new_project_id and new_project_id != last_project_id:
                        last_project_id = new_project_id

                        # Emit project ID update
                        print(f"  🔊 AG-UI: STATE_DELTA (project_id={new_project_id})", flush=True)
                        yield encoder.encode(StateDeltaEvent(
                            type=EventType.STATE_DELTA,
                            delta=[
                                {"op": "replace", "path": "/video_project_id", "value": new_project_id},
                            ],
                        ))
                        last_event_time = time.time()

                # Periodically fetch and emit capture task status
                if event.get("event") == "on_chain_end":
                    node_name = event.get("name", "")

                    # In upload/editor_only mode, also emit capture tasks after load_assets
                    if node_name in ("capture_single", "aggregate", "move_to_next", "load_assets") and last_project_id:
                        tasks = get_capture_tasks_for_project(last_project_id)

                        print(f"  🔊 AG-UI: STATE_DELTA (capture_tasks, completed={sum(1 for t in tasks if t['status'] == 'completed')}/{len(tasks)})", flush=True)
                        yield encoder.encode(StateDeltaEvent(
                            type=EventType.STATE_DELTA,
                            delta=[
                                {"op": "replace", "path": "/capture_tasks", "value": tasks},
                                {"op": "replace", "path": "/captures_completed",
                                 "value": sum(1 for t in tasks if t["status"] == "completed")},
                                {"op": "replace", "path": "/captures_total", "value": len(tasks)},
                            ],
                        ))
                        last_event_time = time.time()

                # 心跳：保持连接活跃
                now = time.time()
                if now - last_event_time > HEARTBEAT_INTERVAL:
                    yield ": heartbeat\n\n"
                    last_event_time = now

                # Small yield to allow other async tasks
                await asyncio.sleep(0)
        else:
            # Normal execution (not resuming)
            print(f"🔄 [PIPELINE] Streaming events from graph...", flush=True)
            async for event in graph.astream_events(
                initial_state,
                config=config,
                version="v2",
            ):
                event_type = event.get("event", "unknown")
                event_name = event.get("name", "")
                print(f"  📡 Event: {event_type} | {event_name}", flush=True)
                # Get current state if possible
                current_state = {}
                try:
                    state_snapshot = graph.get_state(config)
                    if state_snapshot and hasattr(state_snapshot, 'values'):
                        current_state = state_snapshot.values
                except:
                    pass

                # Translate LangGraph event to AG-UI events
                for ag_event in translator.translate(event, current_state):
                    print(f"  🔊 AG-UI: {ag_event.type} | {getattr(ag_event, 'step_name', '')} | {getattr(ag_event, 'delta', '')[:100] if hasattr(ag_event, 'delta') else ''}", flush=True)
                    yield encoder.encode(ag_event)
                    last_event_time = time.time()

                # Check for project ID updates
                if current_state:
                    new_project_id = current_state.get("video_project_id")
                    if new_project_id and new_project_id != last_project_id:
                        last_project_id = new_project_id

                        # Emit project ID update
                        print(f"  🔊 AG-UI: STATE_DELTA (project_id={new_project_id})", flush=True)
                        yield encoder.encode(StateDeltaEvent(
                            type=EventType.STATE_DELTA,
                            delta=[
                                {"op": "replace", "path": "/video_project_id", "value": new_project_id},
                            ],
                        ))
                        last_event_time = time.time()

                # Periodically fetch and emit capture task status
                if event.get("event") == "on_chain_end":
                    node_name = event.get("name", "")

                    # In upload/editor_only mode, also emit capture tasks after load_assets
                    if node_name in ("capture_single", "aggregate", "move_to_next", "load_assets") and last_project_id:
                        tasks = get_capture_tasks_for_project(last_project_id)

                        print(f"  🔊 AG-UI: STATE_DELTA (capture_tasks, completed={sum(1 for t in tasks if t['status'] == 'completed')}/{len(tasks)})", flush=True)
                        yield encoder.encode(StateDeltaEvent(
                            type=EventType.STATE_DELTA,
                            delta=[
                                {"op": "replace", "path": "/capture_tasks", "value": tasks},
                                {"op": "replace", "path": "/captures_completed",
                                 "value": sum(1 for t in tasks if t["status"] == "completed")},
                                {"op": "replace", "path": "/captures_total", "value": len(tasks)},
                            ],
                        ))
                        last_event_time = time.time()

                # 心跳：保持连接活跃
                now = time.time()
                if now - last_event_time > HEARTBEAT_INTERVAL:
                    yield ": heartbeat\n\n"
                    last_event_time = now

                # Small yield to allow other async tasks
                await asyncio.sleep(0)

        # ─────────────────────────────────────────────────────
        # 5. Finalize
        # ─────────────────────────────────────────────────────

        # Close any open message stream
        for ag_event in translator.finalize_message():
            print(f"  🔊 AG-UI: {ag_event.type} (finalize)", flush=True)
            yield encoder.encode(ag_event)

        # Get final state and check for interrupts
        try:
            final_state_snapshot = graph.get_state(config)
            final_state = final_state_snapshot.values if final_state_snapshot else {}

            # Check for interrupts
            if final_state_snapshot and hasattr(final_state_snapshot, 'tasks') and final_state_snapshot.tasks:
                for task in final_state_snapshot.tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        # Found an interrupt - emit RUN_FINISHED with interrupt outcome
                        interrupt_obj = task.interrupts[0]

                        print(f"  🔊 AG-UI: RUN_FINISHED (interrupt)", flush=True)
                        yield encoder.encode(RunFinishedEvent(
                            type=EventType.RUN_FINISHED,
                            thread_id=thread_id,
                            run_id=run_id,
                            outcome="interrupt",
                            interrupt={
                                "id": str(uuid.uuid4()),
                                "reason": "human_input_required",
                                "payload": make_json_safe(interrupt_obj.value) if hasattr(interrupt_obj, 'value') else {}
                            }
                        ))
                        return  # Exit early, don't emit normal completion
        except Exception as e:
            print(f"Error checking for interrupts: {e}")
            final_state = {}

        # No interrupt - normal completion
        final_ui_state = extract_ui_state(final_state)
        final_ui_state["status"] = "completed"
        final_ui_state["progress_percent"] = 100

        # Final capture tasks
        if last_project_id:
            final_ui_state["capture_tasks"] = get_capture_tasks_for_project(last_project_id)

        print(f"  🔊 AG-UI: STATE_SNAPSHOT (final)", flush=True)
        yield encoder.encode(StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot=final_ui_state,
        ))
    
    except Exception as e:
        import traceback
        traceback.print_exc()

        # Emit error
        print(f"  🔊 AG-UI: RUN_ERROR ({str(e)[:100]})", flush=True)
        yield encoder.encode(RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=str(e),
        ))
    
    finally:
        # ─────────────────────────────────────────────────────
        # 6. RUN_FINISHED (only for success/error, not interrupt)
        # ─────────────────────────────────────────────────────
        # Note: If interrupted, we already returned early above
        print(f"  🔊 AG-UI: RUN_FINISHED (success)", flush=True)
        yield encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id,
            outcome="success",
        ))

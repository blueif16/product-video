"""
Translate LangGraph events to AG-UI protocol events.

Maps:
- on_chain_start → STEP_STARTED
- on_chain_end → STEP_FINISHED  
- on_chat_model_stream → TEXT_MESSAGE_CONTENT
- state changes → STATE_DELTA
"""
from typing import Any, Optional
import uuid

from ag_ui.core import (
    EventType,
    StepStartedEvent,
    StepFinishedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    StateDeltaEvent,
    CustomEvent,
)


# Nodes to track as "steps" in UI
TRACKED_NODES = {
    "intake": ("Validating Project", 5),
    "analyze_and_plan": ("Analyzing App", 15),
    "prepare_capture_queue": ("Preparing Captures", 20),
    "capture_single": ("Capturing Screen", None),  # Dynamic progress
    "aggregate": ("Aggregating Results", 50),
    "load_assets": ("Loading Assets", 55),
    "planner": ("Planning Timeline", 60),
    "compose_clips": ("Composing Clips", 70),
    "assemble": ("Assembling Video", 80),
    "render": ("Rendering Video", 90),
    "music_plan": ("Planning Music", 92),
    "music_generate": ("Generating Music", 95),
    "mux_audio": ("Adding Audio", 98),
}


def make_json_safe(obj: Any, seen: Optional[set] = None) -> Any:
    """
    Recursively make object JSON-serializable.
    Handles circular references, Pydantic models, etc.
    """
    if seen is None:
        seen = set()
    
    obj_id = id(obj)
    if obj_id in seen:
        return "[Circular Reference]"
    
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    
    seen.add(obj_id)
    
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v, seen) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_safe(item, seen) for item in obj]
    elif hasattr(obj, "model_dump"):
        return make_json_safe(obj.model_dump(), seen)
    elif hasattr(obj, "__dict__"):
        return make_json_safe(obj.__dict__, seen)
    else:
        return str(obj)


def extract_ui_state(langgraph_state: dict) -> dict:
    """
    Extract UI-relevant state from LangGraph state.
    
    Returns a clean dict suitable for AG-UI STATE_SNAPSHOT/STATE_DELTA.
    """
    # Fields to expose to frontend
    ui_fields = [
        "video_project_id",
        "pipeline_mode",
        "status",
        "current_stage",
        "stage_message",
        "progress_percent",
        "pending_task_ids",
        "current_task_index",
        "completed_task_ids",
        "clip_task_ids",
        "render_status",
        "render_path",
        "audio_path",
        "final_video_path",
    ]
    
    ui_state = {}
    for field in ui_fields:
        if field in langgraph_state:
            ui_state[field] = make_json_safe(langgraph_state[field])
    
    # Compute derived fields
    pending = langgraph_state.get("pending_task_ids", [])
    current_idx = langgraph_state.get("current_task_index", 0)
    completed = langgraph_state.get("completed_task_ids", [])
    
    ui_state["captures_total"] = len(pending) if pending else 0
    ui_state["captures_completed"] = len(completed) if completed else 0
    
    # Calculate capture progress
    if pending and langgraph_state.get("current_stage") == "capturing":
        capture_progress = (current_idx / len(pending)) * 30 + 20  # 20-50%
        ui_state["progress_percent"] = int(capture_progress)
    
    return ui_state


class EventTranslator:
    """
    Translates LangGraph streaming events to AG-UI events.
    
    Usage:
        translator = EventTranslator(thread_id, run_id)
        
        async for event in graph.astream_events(...):
            for ag_event in translator.translate(event, current_state):
                yield ag_event
    """
    
    def __init__(self, thread_id: str, run_id: str):
        self.thread_id = thread_id
        self.run_id = run_id
        self.message_id = str(uuid.uuid4())
        self.in_message = False
        self.last_state_hash = None
        self.current_node = None
    
    def translate(
        self,
        langgraph_event: dict,
        current_state: Optional[dict] = None,
    ) -> list:
        """
        Translate a LangGraph event to AG-UI event(s).
        
        Returns list of AG-UI events (may be empty).
        """
        events = []
        event_type = langgraph_event.get("event")
        
        # ─────────────────────────────────────────────────────
        # Node Start
        # ─────────────────────────────────────────────────────
        if event_type == "on_chain_start":
            node_name = langgraph_event.get("name", "")
            
            if node_name in TRACKED_NODES:
                self.current_node = node_name
                display_name, progress = TRACKED_NODES[node_name]
                
                events.append(StepStartedEvent(
                    type=EventType.STEP_STARTED,
                    step_name=node_name,
                    metadata={"display_name": display_name},
                ))
                
                # Emit progress update
                if progress is not None:
                    events.append(StateDeltaEvent(
                        type=EventType.STATE_DELTA,
                        delta=[
                            {"op": "replace", "path": "/current_stage", "value": node_name},
                            {"op": "replace", "path": "/stage_message", "value": display_name},
                            {"op": "replace", "path": "/progress_percent", "value": progress},
                        ],
                    ))
        
        # ─────────────────────────────────────────────────────
        # Node End
        # ─────────────────────────────────────────────────────
        elif event_type == "on_chain_end":
            node_name = langgraph_event.get("name", "")
            
            if node_name in TRACKED_NODES:
                events.append(StepFinishedEvent(
                    type=EventType.STEP_FINISHED,
                    step_name=node_name,
                ))
                self.current_node = None
        
        # ─────────────────────────────────────────────────────
        # LLM Token Streaming
        # ─────────────────────────────────────────────────────
        elif event_type == "on_chat_model_stream":
            chunk = langgraph_event.get("data", {}).get("chunk")
            
            if chunk and hasattr(chunk, "content") and chunk.content:
                # Start message if needed
                if not self.in_message:
                    events.append(TextMessageStartEvent(
                        type=EventType.TEXT_MESSAGE_START,
                        message_id=self.message_id,
                        role="assistant",
                    ))
                    self.in_message = True

                # Extract text content from chunk
                content = chunk.content
                if isinstance(content, list):
                    # Handle multimodal content (list of dicts)
                    text_parts = [item.get('text', '') for item in content if isinstance(item, dict) and item.get('type') == 'text']
                    content = ''.join(text_parts)
                elif not isinstance(content, str):
                    content = str(content)

                # Only emit if content is non-empty
                if content:
                    events.append(TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=self.message_id,
                        delta=content,
                    ))
        
        # ─────────────────────────────────────────────────────
        # Tool Calls (capture, etc.)
        # ─────────────────────────────────────────────────────
        elif event_type == "on_tool_start":
            tool_name = langgraph_event.get("name", "unknown")
            events.append(CustomEvent(
                type=EventType.CUSTOM,
                name="tool_start",
                value={"tool": tool_name},
            ))
        
        elif event_type == "on_tool_end":
            tool_name = langgraph_event.get("name", "unknown")
            events.append(CustomEvent(
                type=EventType.CUSTOM,
                name="tool_end",
                value={"tool": tool_name},
            ))
        
        return events
    
    def finalize_message(self) -> list:
        """Close any open message stream."""
        events = []
        if self.in_message:
            events.append(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=self.message_id,
            ))
            self.in_message = False
            self.message_id = str(uuid.uuid4())  # New ID for next message
        return events

# AG-UI Integration Guide for StreamLine

**A practical developer guide for integrating AG-UI with your LangGraph-based video production pipeline**

*Target: Python backend (FastAPI + LangGraph 0.3.x) + React/Next.js frontend*

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Core Concepts](#2-core-concepts)
3. [Implementation Guide](#3-implementation-guide)
4. [Gotchas & Debugging](#4-gotchas--debugging)
5. [Production Checklist](#5-production-checklist)

---

## 1. Quick Start

### Get Something Running in 30 Minutes

#### Step 1: Install Dependencies

**Backend (Python):**
```bash
pip install ag-ui-langgraph ag-ui-protocol fastapi uvicorn
# Or with your existing requirements
pip install "ag-ui-langgraph>=0.0.23" "ag-ui-protocol>=0.1.9" --break-system-packages
```

**Frontend (Next.js):**
```bash
npm install @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime @ag-ui/client
```

#### Step 2: Minimal Backend Adapter

Create `ag_ui_adapter.py` alongside your existing StreamLine code:

```python
"""
Minimal AG-UI adapter for StreamLine
Drop-in integration that wraps your existing LangGraph
"""
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import json
from typing import AsyncGenerator

from ag_ui.core import (
    RunAgentInput,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    StateSnapshotEvent,
    StateDeltaEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    StepStartedEvent,
    StepFinishedEvent,
    EventEncoder,
)

# Import your existing graph
from streamline.pipeline import graph  # Your compiled LangGraph

app = FastAPI(title="StreamLine AG-UI")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SSE content type
SSE_CONTENT_TYPE = "text/event-stream"


async def run_streamline_agent(input_data: RunAgentInput) -> AsyncGenerator[str, None]:
    """
    Stream AG-UI events from your LangGraph execution.
    This wraps your existing graph without modifying it.
    """
    encoder = EventEncoder(accept=SSE_CONTENT_TYPE)
    message_id = str(uuid.uuid4())
    
    # 1. Emit RUN_STARTED
    yield encoder.encode(
        RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=input_data.thread_id,
            run_id=input_data.run_id,
        )
    )
    
    # 2. Emit initial STATE_SNAPSHOT
    # Map your PipelineState to AG-UI state
    initial_state = {
        "pipeline_stage": "intake",
        "progress": 0,
        "capture_tasks": [],
        "status": "starting",
    }
    
    yield encoder.encode(
        StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot=initial_state,
        )
    )
    
    try:
        # 3. Get user message from AG-UI input
        user_message = ""
        for msg in input_data.messages:
            if msg.role == "user":
                user_message = msg.content
                break
        
        # 4. Run your existing graph with streaming
        config = {
            "configurable": {
                "thread_id": input_data.thread_id,
            }
        }
        
        # Stream through LangGraph events
        async for event in graph.astream_events(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config,
            version="v2",
        ):
            event_type = event.get("event")
            
            # Map LangGraph events to AG-UI events
            if event_type == "on_chain_start":
                node_name = event.get("name", "unknown")
                yield encoder.encode(
                    StepStartedEvent(
                        type=EventType.STEP_STARTED,
                        step_name=node_name,
                    )
                )
                
                # Emit state delta for stage change
                yield encoder.encode(
                    StateDeltaEvent(
                        type=EventType.STATE_DELTA,
                        delta=[
                            {"op": "replace", "path": "/pipeline_stage", "value": node_name}
                        ],
                    )
                )
            
            elif event_type == "on_chain_end":
                node_name = event.get("name", "unknown")
                yield encoder.encode(
                    StepFinishedEvent(
                        type=EventType.STEP_FINISHED,
                        step_name=node_name,
                    )
                )
            
            elif event_type == "on_chat_model_stream":
                # Stream LLM tokens
                content = event.get("data", {}).get("chunk", {})
                if hasattr(content, "content") and content.content:
                    yield encoder.encode(
                        TextMessageContentEvent(
                            type=EventType.TEXT_MESSAGE_CONTENT,
                            message_id=message_id,
                            delta=content.content,
                        )
                    )
    
    except Exception as e:
        # Emit error as text message
        yield encoder.encode(
            TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=message_id,
                role="assistant",
            )
        )
        yield encoder.encode(
            TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=message_id,
                delta=f"Error: {str(e)}",
            )
        )
        yield encoder.encode(
            TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=message_id,
            )
        )
    
    finally:
        # 5. Always emit RUN_FINISHED
        yield encoder.encode(
            RunFinishedEvent(
                type=EventType.RUN_FINISHED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            )
        )


@app.post("/streamline")
async def streamline_endpoint(input_data: RunAgentInput):
    """AG-UI compatible endpoint for StreamLine."""
    return StreamingResponse(
        run_streamline_agent(input_data),
        media_type=SSE_CONTENT_TYPE,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "streamline-ag-ui"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### Step 3: Minimal Frontend Setup

**`app/api/copilotkit/route.ts`:**
```typescript
import { HttpAgent } from "@ag-ui/client";
import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";

// Connect to your FastAPI backend
const streamlineAgent = new HttpAgent({
  url: "http://127.0.0.1:8000/streamline",
});

const runtime = new CopilotRuntime({
  agents: {
    streamlineAgent,
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};
```

**`app/layout.tsx`:**
```tsx
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <CopilotKit runtimeUrl="/api/copilotkit">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
```

**`app/page.tsx`:**
```tsx
"use client";

import { CopilotChat } from "@copilotkit/react-ui";
import { useCoAgent } from "@copilotkit/react-core";

interface StreamLineState {
  pipeline_stage: string;
  progress: number;
  capture_tasks: Array<{ id: string; status: string }>;
  status: string;
}

export default function StreamLinePage() {
  const { state } = useCoAgent<StreamLineState>({
    name: "streamlineAgent",
    initialState: {
      pipeline_stage: "idle",
      progress: 0,
      capture_tasks: [],
      status: "ready",
    },
  });

  return (
    <div className="flex h-screen">
      {/* Status Panel */}
      <div className="w-64 p-4 border-r">
        <h2 className="font-bold mb-4">Pipeline Status</h2>
        <div className="space-y-2">
          <p>Stage: <span className="font-mono">{state.pipeline_stage}</span></p>
          <p>Progress: {state.progress}%</p>
          <p>Status: {state.status}</p>
        </div>
      </div>
      
      {/* Chat Panel */}
      <div className="flex-1">
        <CopilotChat
          className="h-full"
          labels={{
            initial: "Hi! I'm StreamLine. What video would you like to produce?",
          }}
        />
      </div>
    </div>
  );
}
```

#### Step 4: Run It

```bash
# Terminal 1: Backend
python ag_ui_adapter.py

# Terminal 2: Frontend
npm run dev
```

Visit `http://localhost:3000` and send a message. You should see:
- Chat working with streaming responses
- State panel updating as pipeline progresses

---

## 2. Core Concepts

### AG-UI Event Types (The ~16 You Need to Know)

| Category | Event | Purpose |
|----------|-------|---------|
| **Lifecycle** | `RUN_STARTED` | Agent execution begins |
| | `RUN_FINISHED` | Agent execution completes |
| | `RUN_ERROR` | Agent encountered error |
| | `STEP_STARTED` | Node/step begins (maps to your pipeline stages) |
| | `STEP_FINISHED` | Node/step completes |
| **Text Streaming** | `TEXT_MESSAGE_START` | Begin new message |
| | `TEXT_MESSAGE_CONTENT` | Stream message chunk |
| | `TEXT_MESSAGE_END` | Message complete |
| **Tool Calls** | `TOOL_CALL_START` | Tool invocation begins |
| | `TOOL_CALL_ARGS` | Tool arguments (streamed) |
| | `TOOL_CALL_END` | Tool invocation completes |
| | `TOOL_CALL_RESULT` | Tool returned result |
| **State Sync** | `STATE_SNAPSHOT` | Full state (send at start) |
| | `STATE_DELTA` | Incremental update (JSON Patch RFC 6902) |
| | `MESSAGES_SNAPSHOT` | Full message history |
| **Other** | `CUSTOM` | Your custom events |
| | `RAW` | Pass-through from external systems |

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR EXISTING CODE                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              StreamLine LangGraph Pipeline               │   │
│  │   intake → analyzer → capturer → aggregator → ...       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              AG-UI Adapter (New Layer)                   │   │
│  │   • Wraps graph.astream_events()                        │   │
│  │   • Translates LangGraph events → AG-UI events          │   │
│  │   • Emits STATE_DELTA for UI updates                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼ SSE Stream                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              FastAPI Endpoint (/streamline)              │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ HTTP POST + SSE Response
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (NEW)                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Next.js API Route (/api/copilotkit)         │   │
│  │   • HttpAgent connects to your FastAPI                   │   │
│  │   • CopilotRuntime manages agent lifecycle               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              React Components                            │   │
│  │   • useCoAgent → syncs state                            │   │
│  │   • useCoAgentStateRender → renders state in chat       │   │
│  │   • useLangGraphInterrupt → handles HITL                │   │
│  │   • CopilotChat → chat UI                               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### State Schema Design for StreamLine

Your existing `PipelineState` needs to be mapped to an AG-UI compatible schema:

```python
# Your existing state (keep as-is)
class PipelineState(TypedDict):
    messages: Annotated[list, add_messages]
    video_project_id: str
    capture_tasks: list[dict]
    analysis_summary: str
    status: str

# AG-UI state (what the frontend sees)
# Must be JSON-serializable, flat or shallow nested
AGUIState = TypedDict("AGUIState", {
    # Pipeline progress
    "pipeline_stage": str,  # "intake" | "analyzer" | "capturer" | ...
    "progress": int,  # 0-100
    "status": str,  # "running" | "paused" | "complete" | "error"
    
    # Capture status (for your display tools)
    "capture_tasks": list[dict],  # [{id, name, status, screenshot_url?}]
    "captures_completed": int,
    "captures_total": int,
    
    # Current operation details
    "current_operation": str,  # Human-readable status
    "tool_logs": list[dict],  # [{id, message, status}] for debugging
    
    # Results
    "video_spec": dict | None,  # Final video specification
    "preview_url": str | None,
})
```

---

## 3. Implementation Guide

### 3.1 Display Tools Pattern

Create tools that trigger UI components without modifying your core pipeline.

**Backend: Define Display Tools**

```python
# streamline/display_tools.py
"""
Display tools emit state updates that trigger frontend components.
These don't modify pipeline logic - they just push UI updates.
"""
from typing import Callable
from ag_ui.core import EventType, StateDeltaEvent
import uuid


class DisplayToolEmitter:
    """Helper to emit display tool updates as state deltas."""
    
    def __init__(self, emit_fn: Callable):
        self.emit = emit_fn
    
    async def show_capture_status(
        self,
        completed: list[dict],
        pending: list[dict],
        current: str | None = None,
    ):
        """
        Trigger CaptureStatusGrid component in frontend.
        
        Args:
            completed: [{"id": "1", "name": "Home Screen", "screenshot_url": "..."}]
            pending: [{"id": "2", "name": "Settings", "screenshot_url": None}]
            current: ID of currently capturing task
        """
        await self.emit(
            StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[
                    {
                        "op": "replace",
                        "path": "/capture_tasks",
                        "value": [
                            {**task, "status": "completed"} 
                            for task in completed
                        ] + [
                            {**task, "status": "current" if task["id"] == current else "pending"}
                            for task in pending
                        ],
                    },
                    {
                        "op": "replace",
                        "path": "/captures_completed",
                        "value": len(completed),
                    },
                    {
                        "op": "replace",
                        "path": "/captures_total",
                        "value": len(completed) + len(pending),
                    },
                ],
            )
        )
    
    async def request_user_input(
        self,
        question: str,
        options: list[str] | None = None,
        input_type: str = "text",  # "text" | "select" | "file"
    ):
        """
        Trigger UserInputCard component for HITL.
        
        Frontend renders a question card; user response flows back via interrupt.
        """
        request_id = str(uuid.uuid4())
        await self.emit(
            StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[
                    {
                        "op": "replace",
                        "path": "/user_input_request",
                        "value": {
                            "id": request_id,
                            "question": question,
                            "options": options,
                            "input_type": input_type,
                            "status": "pending",
                        },
                    },
                ],
            )
        )
        return request_id
    
    async def preview_video_spec(self, clips: list[dict]):
        """
        Trigger TimelinePreview component.
        
        Args:
            clips: [{"id": "1", "start": 0, "duration": 3, "screenshot_url": "...", "caption": "..."}]
        """
        await self.emit(
            StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[
                    {
                        "op": "replace",
                        "path": "/video_spec",
                        "value": {
                            "clips": clips,
                            "total_duration": sum(c["duration"] for c in clips),
                        },
                    },
                ],
            )
        )
    
    async def update_tool_log(
        self,
        log_id: str,
        message: str,
        status: str = "processing",  # "processing" | "completed" | "error"
    ):
        """Update tool execution log for debugging visibility."""
        await self.emit(
            StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[
                    {
                        "op": "add",
                        "path": "/tool_logs/-",  # Append to array
                        "value": {
                            "id": log_id,
                            "message": message,
                            "status": status,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    },
                ],
            )
        )
```

**Backend: Use Display Tools in Your Pipeline**

```python
# streamline/nodes/capturer.py
"""Modified capturer node that emits display updates."""
import asyncio
from langgraph.graph import StateGraph
from streamline.display_tools import DisplayToolEmitter


async def capturer_node(state: PipelineState, config: dict):
    """
    Capture screenshots with live UI updates.
    """
    # Get the emit function from config (injected by AG-UI adapter)
    emit_fn = config.get("configurable", {}).get("emit_event")
    display = DisplayToolEmitter(emit_fn) if emit_fn else None
    
    tasks = state["capture_tasks"]
    completed = []
    
    for i, task in enumerate(tasks):
        # Update UI: show current progress
        if display:
            await display.show_capture_status(
                completed=completed,
                pending=tasks[i:],
                current=task["id"],
            )
            await display.update_tool_log(
                log_id=f"capture-{task['id']}",
                message=f"Capturing: {task['name']}",
                status="processing",
            )
        
        # Do the actual capture (your existing logic)
        screenshot_url = await capture_simulator_screenshot(
            task["simulator_id"],
            task["screen_name"],
        )
        
        completed.append({
            **task,
            "screenshot_url": screenshot_url,
        })
        
        # Update UI: mark completed
        if display:
            await display.update_tool_log(
                log_id=f"capture-{task['id']}",
                message=f"Captured: {task['name']}",
                status="completed",
            )
        
        # Small delay for UI to catch up
        await asyncio.sleep(0.1)
    
    # Final status
    if display:
        await display.show_capture_status(
            completed=completed,
            pending=[],
            current=None,
        )
    
    return {"capture_tasks": completed}
```

**Frontend: Map State to Components**

```tsx
// components/CaptureStatusGrid.tsx
"use client";

interface CaptureTask {
  id: string;
  name: string;
  status: "pending" | "current" | "completed";
  screenshot_url?: string;
}

export function CaptureStatusGrid({ tasks }: { tasks: CaptureTask[] }) {
  return (
    <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
      {tasks.map((task) => (
        <div
          key={task.id}
          className={`
            relative rounded-lg overflow-hidden border-2
            ${task.status === "current" ? "border-blue-500 animate-pulse" : ""}
            ${task.status === "completed" ? "border-green-500" : ""}
            ${task.status === "pending" ? "border-gray-300" : ""}
          `}
        >
          {task.screenshot_url ? (
            <img
              src={task.screenshot_url}
              alt={task.name}
              className="w-full aspect-video object-cover"
            />
          ) : (
            <div className="w-full aspect-video bg-gray-200 flex items-center justify-center">
              {task.status === "current" ? (
                <span className="text-blue-500">Capturing...</span>
              ) : (
                <span className="text-gray-400">Pending</span>
              )}
            </div>
          )}
          <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-xs p-1">
            {task.name}
          </div>
        </div>
      ))}
    </div>
  );
}
```

```tsx
// components/TimelinePreview.tsx
"use client";

interface VideoSpec {
  clips: Array<{
    id: string;
    start: number;
    duration: number;
    screenshot_url: string;
    caption?: string;
  }>;
  total_duration: number;
}

export function TimelinePreview({ spec }: { spec: VideoSpec }) {
  return (
    <div className="p-4 bg-gray-900 rounded-lg">
      <div className="flex items-center gap-1 overflow-x-auto pb-2">
        {spec.clips.map((clip, i) => (
          <div
            key={clip.id}
            className="flex-shrink-0 relative"
            style={{ width: `${(clip.duration / spec.total_duration) * 100}%`, minWidth: 60 }}
          >
            <img
              src={clip.screenshot_url}
              alt={`Clip ${i + 1}`}
              className="w-full h-16 object-cover rounded"
            />
            <div className="absolute bottom-0 left-0 right-0 bg-black/70 text-white text-xs p-0.5 truncate">
              {clip.duration}s
            </div>
          </div>
        ))}
      </div>
      <div className="text-gray-400 text-sm mt-2">
        Total: {spec.total_duration}s · {spec.clips.length} clips
      </div>
    </div>
  );
}
```

```tsx
// app/page.tsx - Wire components to state
"use client";

import { useCoAgent, useCoAgentStateRender } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { CaptureStatusGrid } from "@/components/CaptureStatusGrid";
import { TimelinePreview } from "@/components/TimelinePreview";

interface StreamLineState {
  pipeline_stage: string;
  progress: number;
  status: string;
  capture_tasks: Array<{
    id: string;
    name: string;
    status: string;
    screenshot_url?: string;
  }>;
  captures_completed: number;
  captures_total: number;
  video_spec: {
    clips: Array<{
      id: string;
      start: number;
      duration: number;
      screenshot_url: string;
      caption?: string;
    }>;
    total_duration: number;
  } | null;
  tool_logs: Array<{ id: string; message: string; status: string }>;
}

export default function StreamLinePage() {
  const { state } = useCoAgent<StreamLineState>({
    name: "streamlineAgent",
    initialState: {
      pipeline_stage: "idle",
      progress: 0,
      status: "ready",
      capture_tasks: [],
      captures_completed: 0,
      captures_total: 0,
      video_spec: null,
      tool_logs: [],
    },
  });

  // Render components in chat based on state
  useCoAgentStateRender({
    name: "streamlineAgent",
    render: ({ state }) => {
      // Show capture grid when capturing
      if (state.pipeline_stage === "capturer" && state.capture_tasks.length > 0) {
        return <CaptureStatusGrid tasks={state.capture_tasks} />;
      }
      
      // Show timeline when video spec ready
      if (state.video_spec) {
        return <TimelinePreview spec={state.video_spec} />;
      }
      
      // Show progress for other stages
      if (state.status === "running") {
        return (
          <div className="p-4 bg-blue-50 rounded-lg">
            <div className="flex justify-between mb-2">
              <span className="font-medium">{state.pipeline_stage}</span>
              <span>{state.progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all"
                style={{ width: `${state.progress}%` }}
              />
            </div>
          </div>
        );
      }
      
      return null;
    },
  });

  return (
    <div className="flex h-screen">
      <div className="flex-1">
        <CopilotChat
          className="h-full"
          labels={{
            initial: "Hi! I'm StreamLine. Describe the video you want to create.",
          }}
        />
      </div>
    </div>
  );
}
```

### 3.2 HITL Interrupts

Make LangGraph `interrupt()` render as rich UI.

**Backend: Interrupt with Structured Data**

```python
# streamline/nodes/planner.py
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver


async def planner_node(state: PipelineState, config: dict):
    """
    Plan video sequence with human review.
    """
    emit_fn = config.get("configurable", {}).get("emit_event")
    
    # Generate plan
    proposed_clips = await generate_video_plan(state["analysis_summary"])
    
    # Emit state so frontend can preview
    if emit_fn:
        await emit_fn(
            StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[
                    {"op": "replace", "path": "/proposed_plan", "value": proposed_clips},
                ],
            )
        )
    
    # Interrupt for human review
    # The value passed here is what frontend receives in event.value
    decision = interrupt({
        "type": "plan_review",
        "proposed_clips": proposed_clips,
        "question": "Review the proposed video sequence. Approve or suggest changes?",
        "options": ["approve", "modify", "regenerate"],
    })
    
    # Handle response
    if decision["action"] == "approve":
        return {"video_plan": proposed_clips}
    elif decision["action"] == "modify":
        modified = apply_modifications(proposed_clips, decision.get("modifications", []))
        return {"video_plan": modified}
    else:  # regenerate
        return {"video_plan": None, "regenerate": True}


# In your graph setup, enable checkpointing
memory = MemorySaver()
graph = workflow.compile(checkpointer=memory, interrupt_before=["planner"])
```

**Backend: File Picker Interrupt Example**

```python
async def project_selector_node(state: PipelineState, config: dict):
    """
    Let user select Xcode project path.
    """
    # Interrupt with file picker request
    selection = interrupt({
        "type": "file_picker",
        "title": "Select Xcode Project",
        "accept": [".xcodeproj", ".xcworkspace"],
        "question": "Please select your Xcode project to capture screenshots from.",
        "default_path": state.get("last_project_path"),
    })
    
    # Validate selection
    project_path = selection.get("path")
    if not project_path or not Path(project_path).exists():
        raise ValueError(f"Invalid project path: {project_path}")
    
    return {"xcode_project_path": project_path}
```

**Frontend: Handle Interrupts**

```tsx
// components/PlanReviewCard.tsx
"use client";

interface ProposedClip {
  id: string;
  screen_name: string;
  duration: number;
  caption: string;
}

interface PlanReviewProps {
  proposedClips: ProposedClip[];
  onApprove: () => void;
  onModify: (modifications: any[]) => void;
  onRegenerate: () => void;
}

export function PlanReviewCard({
  proposedClips,
  onApprove,
  onModify,
  onRegenerate,
}: PlanReviewProps) {
  const [modifications, setModifications] = useState<any[]>([]);

  return (
    <div className="p-4 bg-white border rounded-lg shadow-sm">
      <h3 className="font-bold mb-4">Review Proposed Video Plan</h3>
      
      <div className="space-y-2 mb-4">
        {proposedClips.map((clip, i) => (
          <div key={clip.id} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
            <span className="text-gray-500">{i + 1}.</span>
            <span className="flex-1">{clip.screen_name}</span>
            <span className="text-sm text-gray-500">{clip.duration}s</span>
          </div>
        ))}
      </div>
      
      <div className="flex gap-2">
        <button
          onClick={onApprove}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          Approve
        </button>
        <button
          onClick={() => onModify(modifications)}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Modify
        </button>
        <button
          onClick={onRegenerate}
          className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
        >
          Regenerate
        </button>
      </div>
    </div>
  );
}
```

```tsx
// components/FilePickerCard.tsx
"use client";

interface FilePickerProps {
  title: string;
  accept: string[];
  defaultPath?: string;
  onSelect: (path: string) => void;
}

export function FilePickerCard({
  title,
  accept,
  defaultPath,
  onSelect,
}: FilePickerProps) {
  const [path, setPath] = useState(defaultPath || "");

  return (
    <div className="p-4 bg-white border rounded-lg shadow-sm">
      <h3 className="font-bold mb-4">{title}</h3>
      
      <input
        type="text"
        value={path}
        onChange={(e) => setPath(e.target.value)}
        placeholder="/path/to/project.xcodeproj"
        className="w-full p-2 border rounded mb-4"
      />
      
      <p className="text-sm text-gray-500 mb-4">
        Accepted: {accept.join(", ")}
      </p>
      
      <button
        onClick={() => onSelect(path)}
        disabled={!path}
        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
      >
        Select
      </button>
    </div>
  );
}
```

```tsx
// app/page.tsx - Wire up interrupt handlers
"use client";

import { useLangGraphInterrupt } from "@copilotkit/react-core";
import { PlanReviewCard } from "@/components/PlanReviewCard";
import { FilePickerCard } from "@/components/FilePickerCard";

export default function StreamLinePage() {
  // ... useCoAgent setup ...

  // Handle plan review interrupts
  useLangGraphInterrupt<{
    type: string;
    proposed_clips?: any[];
    question: string;
    options?: string[];
  }>({
    render: ({ event, resolve }) => {
      const data = event.value;
      
      if (data.type === "plan_review") {
        return (
          <PlanReviewCard
            proposedClips={data.proposed_clips || []}
            onApprove={() => resolve({ action: "approve" })}
            onModify={(mods) => resolve({ action: "modify", modifications: mods })}
            onRegenerate={() => resolve({ action: "regenerate" })}
          />
        );
      }
      
      if (data.type === "file_picker") {
        return (
          <FilePickerCard
            title={data.title || "Select File"}
            accept={data.accept || []}
            defaultPath={data.default_path}
            onSelect={(path) => resolve({ path })}
          />
        );
      }
      
      // Fallback: generic text input
      return (
        <div className="p-4 bg-white border rounded-lg">
          <p className="mb-4">{data.question}</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const form = e.target as HTMLFormElement;
              resolve({ response: form.response.value });
            }}
          >
            <input
              name="response"
              type="text"
              className="w-full p-2 border rounded mb-4"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded"
            >
              Submit
            </button>
          </form>
        </div>
      );
    },
  });

  // ... rest of component ...
}
```

### 3.3 State Streaming

**Understanding STATE_SNAPSHOT vs STATE_DELTA**

```python
# STATE_SNAPSHOT: Send complete state at run start
# Use for: Initial state, after major transitions, recovery
yield encoder.encode(
    StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={
            "pipeline_stage": "intake",
            "progress": 0,
            "status": "running",
            "capture_tasks": [],
            # ... full state
        },
    )
)

# STATE_DELTA: Send incremental updates (JSON Patch RFC 6902)
# Use for: Progress updates, partial state changes
yield encoder.encode(
    StateDeltaEvent(
        type=EventType.STATE_DELTA,
        delta=[
            # Replace operation
            {"op": "replace", "path": "/progress", "value": 50},
            
            # Add to array
            {"op": "add", "path": "/tool_logs/-", "value": {"id": "1", "message": "..."}},
            
            # Remove from array (by index)
            {"op": "remove", "path": "/tool_logs/0"},
            
            # Move within array
            {"op": "move", "from": "/tool_logs/0", "path": "/tool_logs/2"},
            
            # Nested path
            {"op": "replace", "path": "/video_spec/total_duration", "value": 45},
        ],
    )
)
```

**Helper: Auto-Delta Calculation**

```python
# streamline/ag_ui_helpers.py
import jsonpatch
from typing import Any


class StateDeltaHelper:
    """
    Automatically calculate and emit state deltas.
    """
    
    def __init__(self, emit_fn):
        self.emit = emit_fn
        self._current_state: dict = {}
        self._initialized = False
    
    async def initialize(self, initial_state: dict):
        """Send initial STATE_SNAPSHOT."""
        self._current_state = initial_state.copy()
        self._initialized = True
        
        await self.emit(
            StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                snapshot=initial_state,
            )
        )
    
    async def update(self, new_state: dict):
        """
        Calculate delta and emit STATE_DELTA.
        Only emits if there are actual changes.
        """
        if not self._initialized:
            await self.initialize(new_state)
            return
        
        # Calculate JSON Patch
        patch = jsonpatch.make_patch(self._current_state, new_state)
        patch_list = list(patch)
        
        if patch_list:
            await self.emit(
                StateDeltaEvent(
                    type=EventType.STATE_DELTA,
                    delta=patch_list,
                )
            )
            self._current_state = new_state.copy()
    
    async def update_field(self, path: str, value: Any):
        """Update a single field efficiently."""
        # Apply to local state
        parts = path.strip("/").split("/")
        obj = self._current_state
        for part in parts[:-1]:
            obj = obj[part]
        obj[parts[-1]] = value
        
        # Emit delta
        await self.emit(
            StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[{"op": "replace", "path": f"/{path}", "value": value}],
            )
        )


# Usage in adapter
async def run_agent_with_state_tracking(input_data: RunAgentInput):
    encoder = EventEncoder(accept=SSE_CONTENT_TYPE)
    state_helper = StateDeltaHelper(lambda e: encoder.encode(e))
    
    # Initialize
    await state_helper.initialize({
        "pipeline_stage": "intake",
        "progress": 0,
        "status": "running",
    })
    
    # Update progress efficiently
    for i in range(10):
        await state_helper.update_field("progress", i * 10)
        await asyncio.sleep(0.1)
```

### 3.4 Project Structure

```
streamline/
├── backend/
│   ├── streamline/
│   │   ├── __init__.py
│   │   ├── pipeline.py          # Your existing LangGraph
│   │   ├── state.py             # PipelineState definition
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── intake.py
│   │   │   ├── analyzer.py
│   │   │   ├── capturer.py      # Modified with display tools
│   │   │   └── ...
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── bash_tools.py    # Your existing tools
│   │       └── db_tools.py
│   │
│   ├── ag_ui/                   # NEW: AG-UI integration layer
│   │   ├── __init__.py
│   │   ├── adapter.py           # Main AG-UI adapter
│   │   ├── display_tools.py     # Display tool emitter
│   │   ├── state_helpers.py     # Delta calculation helpers
│   │   └── event_translator.py  # LangGraph → AG-UI event mapping
│   │
│   ├── main.py                  # FastAPI app with AG-UI endpoint
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── app/
│   │   ├── api/
│   │   │   └── copilotkit/
│   │   │       └── route.ts     # CopilotKit API route
│   │   ├── layout.tsx           # CopilotKit provider
│   │   ├── page.tsx             # Main UI with hooks
│   │   └── globals.css
│   │
│   ├── components/
│   │   ├── ui/                  # Shadcn/Tailwind components
│   │   ├── CaptureStatusGrid.tsx
│   │   ├── TimelinePreview.tsx
│   │   ├── PlanReviewCard.tsx
│   │   ├── FilePickerCard.tsx
│   │   └── ToolLogs.tsx
│   │
│   ├── lib/
│   │   ├── types.ts             # Shared TypeScript types
│   │   └── hooks/
│   │       └── useStreamLine.ts # Custom hook for StreamLine state
│   │
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.ts
│
└── shared/
    └── types/
        └── state.ts             # Shared state schema (if using codegen)
```

**`shared/types/state.ts`** (TypeScript equivalent of your Python state):

```typescript
// Shared type definitions for AG-UI state
// Keep in sync with backend AGUIState

export interface CaptureTask {
  id: string;
  name: string;
  status: "pending" | "current" | "completed" | "error";
  screenshot_url?: string;
  error_message?: string;
}

export interface VideoClip {
  id: string;
  start: number;
  duration: number;
  screenshot_url: string;
  caption?: string;
}

export interface VideoSpec {
  clips: VideoClip[];
  total_duration: number;
}

export interface ToolLog {
  id: string;
  message: string;
  status: "processing" | "completed" | "error";
  timestamp: string;
}

export interface UserInputRequest {
  id: string;
  question: string;
  options?: string[];
  input_type: "text" | "select" | "file";
  status: "pending" | "answered";
}

export interface StreamLineState {
  // Pipeline progress
  pipeline_stage: string;
  progress: number;
  status: "idle" | "running" | "paused" | "complete" | "error";
  
  // Capture tracking
  capture_tasks: CaptureTask[];
  captures_completed: number;
  captures_total: number;
  
  // Current operation
  current_operation: string;
  tool_logs: ToolLog[];
  
  // Results
  video_spec: VideoSpec | null;
  preview_url: string | null;
  
  // HITL
  user_input_request: UserInputRequest | null;
  proposed_plan: VideoClip[] | null;
}

// Initial state factory
export const createInitialState = (): StreamLineState => ({
  pipeline_stage: "idle",
  progress: 0,
  status: "idle",
  capture_tasks: [],
  captures_completed: 0,
  captures_total: 0,
  current_operation: "",
  tool_logs: [],
  video_spec: null,
  preview_url: null,
  user_input_request: null,
  proposed_plan: null,
});
```

### 3.5 Incremental Adoption Phases

#### Phase 1: Basic Chat + Tool Visibility (1-2 days)

**Goal:** Get AG-UI running without modifying pipeline logic.

```python
# backend/ag_ui/adapter.py - Phase 1: Passthrough adapter
async def run_agent_stream(input_data: RunAgentInput):
    """Minimal adapter that just streams LangGraph output."""
    encoder = EventEncoder(accept=SSE_CONTENT_TYPE)
    message_id = str(uuid.uuid4())
    
    yield encoder.encode(RunStartedEvent(
        type=EventType.RUN_STARTED,
        thread_id=input_data.thread_id,
        run_id=input_data.run_id,
    ))
    
    yield encoder.encode(TextMessageStartEvent(
        type=EventType.TEXT_MESSAGE_START,
        message_id=message_id,
        role="assistant",
    ))
    
    # Run your existing graph
    async for event in graph.astream_events(...):
        if event["event"] == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and chunk.content:
                yield encoder.encode(TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=chunk.content,
                ))
    
    yield encoder.encode(TextMessageEndEvent(...))
    yield encoder.encode(RunFinishedEvent(...))
```

**Frontend:** Just `CopilotChat` with no custom state rendering.

#### Phase 2: Custom Status Components (2-3 days)

**Goal:** Add state streaming and basic status display.

**Backend changes:**
- Add `StateDeltaHelper` for state tracking
- Inject `emit_event` into graph config
- Emit `STEP_STARTED`/`STEP_FINISHED` for node transitions

**Frontend changes:**
- Add `useCoAgent` with full state schema
- Add `useCoAgentStateRender` for progress display
- Create basic status components

#### Phase 3: Rich HITL Interrupts (2-3 days)

**Goal:** Replace text-based interrupts with rich UI.

**Backend changes:**
- Enable checkpointing in graph
- Structure interrupt values with `type` field
- Add file picker and plan review interrupts

**Frontend changes:**
- Add `useLangGraphInterrupt` with render function
- Create interrupt-specific components
- Handle user responses

#### Phase 4: Full Dashboard (1 week)

**Goal:** Multiple panels, real-time updates, production polish.

**Components:**
- Pipeline stage visualization
- Live capture grid
- Timeline editor
- Tool execution log
- Error recovery UI

---

## 4. Gotchas & Debugging

### Known Issues (as of January 2026)

#### 1. State Serialization Failures

**Problem:** `RecursionError` or `TypeError: Object is not JSON serializable` when emitting state.

**Cause:** LangGraph internal state contains circular references or non-serializable objects.

**Solution:**
```python
# Always sanitize state before emitting
def make_json_safe(obj, seen=None):
    """Recursively make object JSON-serializable."""
    if seen is None:
        seen = set()
    
    obj_id = id(obj)
    if obj_id in seen:
        return "[Circular Reference]"
    seen.add(obj_id)
    
    if isinstance(obj, dict):
        return {k: make_json_safe(v, seen) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(item, seen) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif hasattr(obj, "model_dump"):  # Pydantic
        return make_json_safe(obj.model_dump(), seen)
    else:
        return str(obj)

# Use when emitting state
safe_state = make_json_safe(raw_state)
yield encoder.encode(StateSnapshotEvent(snapshot=safe_state))
```

#### 2. Event Ordering Errors

**Problem:** `Cannot send event type 'TEXT_MESSAGE_START' after 'TOOL_CALL_START'`

**Cause:** CopilotKit enforces strict serial ordering, but LangGraph may emit overlapping events.

**Solution:**
```python
# Queue events and emit in order
class OrderedEventEmitter:
    def __init__(self):
        self.pending_tool_calls: set[str] = set()
        self.queue: list = []
    
    async def emit(self, event):
        if event.type == EventType.TOOL_CALL_START:
            self.pending_tool_calls.add(event.tool_call_id)
        elif event.type == EventType.TOOL_CALL_END:
            self.pending_tool_calls.discard(event.tool_call_id)
        
        # Buffer text events if tool call in progress
        if event.type.startswith("TEXT_MESSAGE") and self.pending_tool_calls:
            self.queue.append(event)
        else:
            yield event
            # Flush queue when tool calls complete
            if not self.pending_tool_calls:
                for queued in self.queue:
                    yield queued
                self.queue.clear()
```

#### 3. Duplicate State Renders

**Problem:** `useCoAgentStateRender` content duplicated after interrupt resume.

**Cause:** Known bug (#2151) when combining `useLangGraphInterrupt` with `useCoAgentStateRender`.

**Workaround:**
```tsx
// Use key to force re-render
useCoAgentStateRender({
  name: "streamlineAgent",
  render: ({ state }) => (
    <div key={`${state.pipeline_stage}-${state.progress}`}>
      {/* Your component */}
    </div>
  ),
});
```

#### 4. Persistence Issues After Resume

**Problem:** Agent fails to load conversation history from database.

**Cause:** AG-UI message format doesn't match LangGraph checkpoint format.

**Solution:**
```python
# Translate AG-UI messages to LangGraph format
def translate_messages(ag_ui_messages: list[Message]) -> list[dict]:
    result = []
    for msg in ag_ui_messages:
        if msg.role == "user":
            result.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            result.append(AIMessage(content=msg.content))
    return result

# In your endpoint
async def run_agent(input_data: RunAgentInput):
    messages = translate_messages(input_data.messages)
    # Use messages with your graph
```

#### 5. SSE Connection Drops

**Problem:** Frontend loses connection mid-stream.

**Solution:**
```python
# Add heartbeat events
async def run_agent_with_heartbeat(input_data: RunAgentInput):
    encoder = EventEncoder(accept=SSE_CONTENT_TYPE)
    last_event_time = time.time()
    
    async for event in your_event_stream():
        yield encoder.encode(event)
        last_event_time = time.time()
        
        # Send heartbeat every 15 seconds of silence
        if time.time() - last_event_time > 15:
            yield ": heartbeat\n\n"  # SSE comment, keeps connection alive
            last_event_time = time.time()
```

### Debugging Tools

**1. Event Inspector Middleware:**
```python
# backend/ag_ui/debug.py
import logging

logger = logging.getLogger("ag_ui.events")

def debug_event_middleware(emit_fn):
    """Wrap emit function to log all events."""
    async def wrapped(event):
        logger.info(f"AG-UI Event: {event.type} | {json.dumps(event.model_dump(), default=str)[:200]}")
        return await emit_fn(event)
    return wrapped
```

**2. Frontend Event Viewer:**
```tsx
// components/debug/EventViewer.tsx
import { useEffect, useState } from "react";

export function EventViewer() {
  const [events, setEvents] = useState<any[]>([]);
  
  useEffect(() => {
    // Intercept fetch to log SSE events (dev only)
    if (process.env.NODE_ENV === "development") {
      const originalFetch = window.fetch;
      window.fetch = async (...args) => {
        const response = await originalFetch(...args);
        if (response.headers.get("content-type")?.includes("text/event-stream")) {
          const reader = response.body?.getReader();
          // Clone and log events...
        }
        return response;
      };
    }
  }, []);
  
  return (
    <div className="fixed bottom-0 right-0 w-96 h-64 bg-black text-green-400 p-2 overflow-auto font-mono text-xs">
      {events.map((e, i) => (
        <div key={i}>{JSON.stringify(e)}</div>
      ))}
    </div>
  );
}
```

**3. Test Endpoint:**
```python
# Verify AG-UI compliance
@app.get("/test-events")
async def test_events():
    """Return a test SSE stream for debugging."""
    async def generate():
        encoder = EventEncoder(accept=SSE_CONTENT_TYPE)
        
        yield encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id="test",
            run_id="test",
        ))
        
        yield encoder.encode(StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot={"test": "state"},
        ))
        
        yield encoder.encode(TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id="test",
            role="assistant",
        ))
        
        for word in ["Hello", " ", "World", "!"]:
            yield encoder.encode(TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="test",
                delta=word,
            ))
            await asyncio.sleep(0.1)
        
        yield encoder.encode(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id="test",
        ))
        
        yield encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id="test",
            run_id="test",
        ))
    
    return StreamingResponse(generate(), media_type=SSE_CONTENT_TYPE)
```

---

## 5. Production Checklist

### Before Demo

- [ ] **Backend Health**
  - [ ] `/health` endpoint returns 200
  - [ ] SSE stream completes without errors
  - [ ] State snapshots are JSON-serializable
  - [ ] No recursive state structures

- [ ] **Frontend Connection**
  - [ ] HttpAgent URL matches backend
  - [ ] CORS configured for production domain
  - [ ] CopilotKit provider wraps app

- [ ] **State Sync**
  - [ ] Initial state matches backend schema
  - [ ] State deltas apply correctly
  - [ ] UI updates without full re-render

- [ ] **HITL (if enabled)**
  - [ ] Interrupts render correct component
  - [ ] User responses flow back to graph
  - [ ] Graph resumes correctly after interrupt

- [ ] **Error Handling**
  - [ ] Network errors show user-friendly message
  - [ ] Backend errors don't crash frontend
  - [ ] Retry logic for transient failures

### Performance

- [ ] State deltas under 10KB (use snapshots sparingly)
- [ ] Event stream latency < 100ms
- [ ] No memory leaks on long sessions
- [ ] Debounce rapid state updates (16ms minimum)

### Security

- [ ] No sensitive data in AG-UI state
- [ ] CORS restricted to allowed origins
- [ ] Rate limiting on endpoint
- [ ] Input validation on RunAgentInput

### Monitoring

```python
# Add to your FastAPI app
from prometheus_client import Counter, Histogram

ag_ui_events = Counter("ag_ui_events_total", "AG-UI events emitted", ["event_type"])
ag_ui_latency = Histogram("ag_ui_stream_latency_seconds", "Time to first event")

# In your endpoint
@app.post("/streamline")
async def streamline_endpoint(input_data: RunAgentInput):
    start_time = time.time()
    first_event_sent = False
    
    async def tracked_stream():
        nonlocal first_event_sent
        async for event in run_streamline_agent(input_data):
            if not first_event_sent:
                ag_ui_latency.observe(time.time() - start_time)
                first_event_sent = True
            
            # Parse event type from SSE data
            if "data:" in event:
                try:
                    data = json.loads(event.split("data:")[1].strip())
                    ag_ui_events.labels(event_type=data.get("type", "unknown")).inc()
                except:
                    pass
            
            yield event
    
    return StreamingResponse(tracked_stream(), media_type=SSE_CONTENT_TYPE)
```

---

## Quick Reference Card

### Event Emission Pattern
```python
from ag_ui.core import EventEncoder, EventType, *Event

encoder = EventEncoder(accept="text/event-stream")
yield encoder.encode(SomeEvent(type=EventType.SOME_EVENT, ...))
```

### State Update Pattern
```python
# Full state
yield encoder.encode(StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot={...}))

# Incremental (JSON Patch)
yield encoder.encode(StateDeltaEvent(type=EventType.STATE_DELTA, delta=[
    {"op": "replace", "path": "/field", "value": "new"},
    {"op": "add", "path": "/array/-", "value": "item"},
]))
```

### Frontend Hooks
```tsx
// State sync
const { state, setState } = useCoAgent<MyState>({ name: "agent", initialState: {...} });

// Render in chat
useCoAgentStateRender({ name: "agent", render: ({ state }) => <Component {...state} /> });

// Handle interrupts
useLangGraphInterrupt({ render: ({ event, resolve }) => <Card onSubmit={(v) => resolve(v)} /> });
```

### Packages
```
# Python
ag-ui-langgraph>=0.0.23
ag-ui-protocol>=0.1.9

# JavaScript
@copilotkit/react-core
@copilotkit/react-ui
@copilotkit/runtime
@ag-ui/client
```

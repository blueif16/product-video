/**
 * StreamLine Pipeline State
 *
 * Mirrors the AG-UI state emitted by the backend.
 */

export interface CaptureTask {
  id: string;
  description: string;
  status: "pending" | "capturing" | "completed" | "failed";
  asset_url?: string;
  capture_type: "screenshot" | "recording";
}

export interface ClipSpec {
  id: string;
  startFrame: number;
  durationFrames: number;
  layers: any[]; // Simplified for now
}

export interface VideoSpec {
  meta: {
    title: string;
    durationFrames: number;
    fps: number;
    resolution: { width: number; height: number };
  };
  clips: ClipSpec[];
}

export interface StreamLineState {
  // Pipeline identity
  video_project_id: string | null;
  pipeline_mode: "full" | "editor_only" | "upload";

  // Progress
  status: "starting" | "capturing" | "editing" | "rendering" | "completed" | "error";
  current_stage: string;
  stage_message: string;
  progress_percent: number;

  // Capture phase
  capture_tasks: CaptureTask[];
  captures_total: number;
  captures_completed: number;

  // Editor phase
  clip_task_ids: string[];

  // Render phase
  render_status: string | null;
  render_path: string | null;

  // Music phase
  audio_path: string | null;
  final_video_path: string | null;
}

export const initialState: StreamLineState = {
  video_project_id: null,
  pipeline_mode: "full",
  status: "starting",
  current_stage: "idle",
  stage_message: "Ready to create your video",
  progress_percent: 0,
  capture_tasks: [],
  captures_total: 0,
  captures_completed: 0,
  clip_task_ids: [],
  render_status: null,
  render_path: null,
  audio_path: null,
  final_video_path: null,
};

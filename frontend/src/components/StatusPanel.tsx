"use client";

import { StreamLineState } from "@/lib/types";
import { CaptureGrid } from "./CaptureGrid";
import { ProgressBar } from "./ProgressBar";

interface StatusPanelProps {
  state: StreamLineState;
}

export function StatusPanel({ state }: StatusPanelProps) {
  return (
    <div className="p-4 space-y-6">
      {/* Progress */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Progress
        </h2>
        <ProgressBar
          percent={state.progress_percent}
          status={state.status}
        />
        <p className="text-sm text-gray-300 mt-2">{state.stage_message}</p>
      </div>

      {/* Pipeline Info */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Pipeline
        </h2>
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">Mode</span>
            <span className="text-gray-300">{state.pipeline_mode}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Stage</span>
            <span className="text-gray-300">{state.current_stage}</span>
          </div>
          {state.video_project_id && (
            <div className="flex justify-between">
              <span className="text-gray-500">Project</span>
              <span className="text-gray-300 font-mono text-xs">
                {state.video_project_id.slice(0, 8)}...
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Captures */}
      {state.capture_tasks && state.capture_tasks.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Captures ({state.captures_completed}/{state.captures_total})
          </h2>
          <CaptureGrid tasks={state.capture_tasks} />
        </div>
      )}

      {/* Results */}
      {(state.render_path || state.final_video_path) && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Output
          </h2>
          {state.final_video_path && (
            <a
              href={state.final_video_path}
              className="text-blue-400 hover:underline text-sm"
              target="_blank"
            >
              🎬 Download Video
            </a>
          )}
        </div>
      )}
    </div>
  );
}

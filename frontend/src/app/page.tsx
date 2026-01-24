"use client";

import { useState, useEffect } from "react";
import { useCoAgent, useCoAgentStateRender, useLangGraphInterrupt, useCopilotChat } from "@copilotkit/react-core";
import { TextMessage, MessageRole } from "@copilotkit/runtime-client-gql";
import { CopilotChat } from "@copilotkit/react-ui";
import { StreamLineState, initialState } from "@/lib/types";
import { StatusPanel } from "@/components/StatusPanel";
import { CaptureGrid } from "@/components/CaptureGrid";
import { ProgressBar } from "@/components/ProgressBar";
import { InterruptCard } from "@/components/InterruptCard";
import { UploadMode } from "@/components/UploadMode";
import { Settings, Sparkles, Upload as UploadIcon, CheckCircle2, Download, ExternalLink } from "lucide-react";

type PipelineMode = "full" | "upload";

export default function Home() {
  const [mode, setMode] = useState<PipelineMode>("full");
  const [isProcessing, setIsProcessing] = useState(false);

  const { state, setState } = useCoAgent<StreamLineState>({
    name: "pipelineAgent",
    initialState,
  });

  const { appendMessage } = useCopilotChat();

  // 🔴 DIAGNOSTIC: Log every state change
  useEffect(() => {
    console.log('🔴 AGENT STATE CHANGED:', {
      stage: state.current_stage,
      progress: state.progress_percent,
      status: state.status,
      project_id: state.video_project_id,
    });
  }, [state]);

  // Handle upload mode start
  const handleUploadStart = async (
    userInput: string,
    assets: { url: string; description: string }[]
  ) => {
    try {
      setIsProcessing(true);

      // Step 1: Create project from uploads
      console.log("📤 Creating project from", assets.length, "assets");
      const response = await fetch("http://127.0.0.1:8000/projects/from-uploads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: userInput, assets }),
      });

      const { project_id, asset_count } = await response.json();
      console.log("✅ Project created:", project_id, "with", asset_count, "assets");

      // Step 2: Update state with project info
      setState({
        ...state,
        video_project_id: project_id,
        pipeline_mode: "upload",
      });

      // Step 3: Switch to chat view
      setMode("full");

      // Step 4: Trigger agent execution via CopilotKit
      console.log("🚀 Triggering pipeline execution for upload mode...");
      await appendMessage(
        new TextMessage({
          role: MessageRole.User,
          content: `Start editing the uploaded assets to create: ${userInput}. Project ID: ${project_id}`,
        })
      );
    } catch (error) {
      console.error("❌ Upload start failed:", error);
      alert("Failed to start upload pipeline. Check console for details.");
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle interrupts
  useLangGraphInterrupt<{ question: string; hint?: string }>({
    render: ({ event, resolve }) => {
      const data = event.value;

      return (
        <InterruptCard
          question={data.question}
          hint={data.hint}
          onSubmit={(response) => resolve(response)}
        />
      );
    },
  });

  // Render state updates in chat
  useCoAgentStateRender({
    name: "pipelineAgent",
    render: ({ state }) => {
      // Show capture grid during capture phase
      if (state.current_stage === "capture_single" && state.capture_tasks?.length > 0) {
        return (
          <div className="p-4 bg-gray-800 rounded-lg my-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-300">
                Capturing Screenshots
              </span>
              <span className="text-xs text-gray-500">
                {state.captures_completed}/{state.captures_total}
              </span>
            </div>
            <CaptureGrid tasks={state.capture_tasks.slice(0, 6)} />
          </div>
        );
      }

      // Show progress for other stages
      if (state.status === "capturing" || state.status === "editing" || state.status === "rendering") {
        return (
          <div className="p-4 bg-gray-800 rounded-lg my-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-300">
                {state.stage_message}
              </span>
              <span className="text-xs text-gray-500">
                {state.progress_percent}%
              </span>
            </div>
            <ProgressBar percent={state.progress_percent} status={state.status} />
          </div>
        );
      }

      // Show completion
      if (state.status === "completed" && state.final_video_path) {
        return (
          <div className="relative overflow-hidden rounded-xl border border-green-500/30 bg-gradient-to-br from-green-900/40 via-green-800/30 to-emerald-900/40 p-6 my-3 shadow-lg shadow-green-900/20">
            {/* Animated background effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-green-500/5 to-emerald-500/5 animate-pulse" />

            <div className="relative">
              {/* Success icon and title */}
              <div className="flex items-center gap-3 mb-4">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center ring-2 ring-green-500/50">
                  <CheckCircle2 className="w-6 h-6 text-green-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-green-300">视频制作完成！</h3>
                  <p className="text-sm text-gray-400">您的视频已准备好下载</p>
                </div>
              </div>

              {/* Download button */}
              <a
                href={state.final_video_path}
                target="_blank"
                rel="noopener noreferrer"
                className="group inline-flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white font-medium rounded-lg transition-all duration-200 shadow-lg shadow-green-900/30 hover:shadow-green-900/50 hover:scale-[1.02] active:scale-[0.98]"
              >
                <Download className="w-4 h-4" />
                <span>下载视频</span>
                <ExternalLink className="w-3 h-3 opacity-70 group-hover:opacity-100 transition-opacity" />
              </a>
            </div>
          </div>
        );
      }

      return null;
    },
  });

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Status Panel */}
      <div className="w-80 border-r border-gray-700 bg-gray-800 overflow-y-auto">
        <StatusPanel state={state || initialState} />
      </div>

      {/* Main Panel */}
      <div className="flex-1 flex flex-col">
        {/* Header with Mode Toggle */}
        <header className="border-b border-gray-700">
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h1 className="text-xl font-bold text-white">StreamLine</h1>
                <p className="text-sm text-gray-400">AI-Powered Video Production</p>
              </div>
              <button className="p-2 text-gray-400 hover:text-white transition-colors">
                <Settings className="w-5 h-5" />
              </button>
            </div>

            {/* Mode Tabs */}
            <div className="flex gap-2">
              <button
                onClick={() => setMode("full")}
                disabled={isProcessing}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all
                  ${mode === "full"
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                    : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  }
                  ${isProcessing ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
                `}
              >
                <Sparkles className="w-4 h-4" />
                Full Pipeline
              </button>
              <button
                onClick={() => setMode("upload")}
                disabled={isProcessing}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all
                  ${mode === "upload"
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                    : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  }
                  ${isProcessing ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
                `}
              >
                <UploadIcon className="w-4 h-4" />
                Upload Assets
              </button>
            </div>
          </div>

          {/* Mode Description */}
          <div className="px-4 pb-3 border-t border-gray-700 pt-2 bg-gray-800/50">
            {mode === "full" ? (
              <p className="text-xs text-gray-400">
                <span className="font-semibold text-blue-400">Full Pipeline:</span> I'll capture your iOS app screens, plan the video structure, and render everything automatically.
              </p>
            ) : (
              <p className="text-xs text-gray-400">
                <span className="font-semibold text-blue-400">Upload Mode:</span> Upload your existing screenshots, and I'll create a polished promo video from them.
              </p>
            )}
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {mode === "full" ? (
            <CopilotChat
              className="h-full"
              labels={{
                initial: "Hi! I'm StreamLine. Tell me about your app and what kind of promo video you'd like to create.\n\n**Example:** \"I have a fitness app at ~/Code/FitTracker - create a 30 second energetic Product Hunt video\"",
                placeholder: "Describe your app and video goals...",
              }}
            />
          ) : (
            <div className="h-full overflow-y-auto">
              <UploadMode onStart={handleUploadStart} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

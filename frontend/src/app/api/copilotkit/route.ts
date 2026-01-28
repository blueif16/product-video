import { HttpAgent } from "@ag-ui/client";
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";

// 自托管环境：无超时限制
export const maxDuration = 0; // 无限制
export const dynamic = 'force-dynamic';

// Service adapter for CopilotKit (required parameter)
const serviceAdapter = new ExperimentalEmptyAdapter();

// Create agent once at module level (reused across requests)
const pipelineAgent = new HttpAgent({
  url: process.env.PIPELINE_API_URL || "http://127.0.0.1:8000/pipeline",
});

const runtime = new CopilotRuntime({
  agents: {
    pipelineAgent,
  },
});

// Initialize endpoint handler at module level (reused across requests)
const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
  runtime,
  serviceAdapter,
  endpoint: "/api/copilotkit",
});

export const POST = async (req: NextRequest) => {
  return handleRequest(req);
};

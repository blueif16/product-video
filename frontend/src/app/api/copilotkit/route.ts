import { HttpAgent } from "@ag-ui/client";
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";

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

export async function POST(req: NextRequest) {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
}

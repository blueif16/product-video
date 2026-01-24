"use client";

import { Loader2 } from "lucide-react";

interface LoadingOverlayProps {
  message?: string;
}

export function LoadingOverlay({ message = "Loading..." }: LoadingOverlayProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 p-6 rounded-lg flex items-center gap-4">
        <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
        <span className="text-white">{message}</span>
      </div>
    </div>
  );
}

"use client";

import { CaptureTask } from "@/lib/types";
import { CheckCircle, Clock, Loader2, XCircle } from "lucide-react";

interface CaptureGridProps {
  tasks: CaptureTask[];
}

export function CaptureGrid({ tasks }: CaptureGridProps) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {tasks.map((task) => (
        <div
          key={task.id}
          className="relative rounded-lg overflow-hidden bg-gray-700 aspect-[9/16]"
        >
          {/* Thumbnail */}
          {task.asset_url ? (
            <img
              src={task.asset_url}
              alt={task.description}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              {task.status === "capturing" ? (
                <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
              ) : task.status === "pending" ? (
                <Clock className="w-6 h-6 text-gray-500" />
              ) : (
                <XCircle className="w-6 h-6 text-red-400" />
              )}
            </div>
          )}

          {/* Status Badge */}
          <div className="absolute top-1 right-1">
            {task.status === "completed" && (
              <CheckCircle className="w-4 h-4 text-green-400" />
            )}
            {task.status === "capturing" && (
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
            )}
          </div>

          {/* Label */}
          <div className="absolute bottom-0 left-0 right-0 bg-black/60 p-1">
            <p className="text-xs text-white truncate">{task.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

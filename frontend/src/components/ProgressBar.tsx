"use client";

interface ProgressBarProps {
  percent: number;
  status: string;
}

export function ProgressBar({ percent, status }: ProgressBarProps) {
  const getColor = () => {
    if (status === "error") return "bg-red-500";
    if (status === "completed") return "bg-green-500";
    return "bg-blue-500";
  };

  return (
    <div className="w-full bg-gray-700 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all duration-300 ${getColor()}`}
        style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
      />
    </div>
  );
}

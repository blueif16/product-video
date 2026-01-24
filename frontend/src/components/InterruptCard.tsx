"use client";

import { useState } from "react";

interface InterruptCardProps {
  question: string;
  hint?: string;
  onSubmit: (response: string) => void;
}

export function InterruptCard({ question, hint, onSubmit }: InterruptCardProps) {
  const [value, setValue] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim()) {
      onSubmit(value.trim());
      setValue("");
    }
  };

  return (
    <div className="p-4 bg-yellow-900/30 border border-yellow-700 rounded-lg my-2">
      <p className="text-yellow-400 font-medium mb-2">⚠️ Input Required</p>
      <p className="text-gray-300 mb-2">{question}</p>
      {hint && (
        <p className="text-gray-500 text-sm mb-3">Hint: {hint}</p>
      )}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Enter your response..."
          className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded text-sm font-medium"
        >
          Submit
        </button>
      </form>
    </div>
  );
}

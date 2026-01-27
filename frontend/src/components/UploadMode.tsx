"use client";

import { useState, useCallback } from "react";
import { Upload, X, Image as ImageIcon } from "lucide-react";

interface UploadedAsset {
  file: File;
  preview: string;
  description: string;
}

interface UploadModeProps {
  onStart: (userInput: string, assets: { url: string; description: string }[]) => void;
}

export function UploadMode({ onStart }: UploadModeProps) {
  const [assets, setAssets] = useState<UploadedAsset[]>([]);
  const [userInput, setUserInput] = useState("");
  const [uploading, setUploading] = useState(false);

  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files) return;

    const newAssets: UploadedAsset[] = [];

    Array.from(files).forEach((file) => {
      if (file.type.startsWith("image/")) {
        const preview = URL.createObjectURL(file);
        newAssets.push({
          file,
          preview,
          description: file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " "),
        });
      }
    });

    setAssets((prev) => [...prev, ...newAssets]);
  }, []);

  const removeAsset = (index: number) => {
    setAssets((prev) => {
      const updated = [...prev];
      URL.revokeObjectURL(updated[index].preview);
      updated.splice(index, 1);
      return updated;
    });
  };

  const handleSubmit = async () => {
    if (!userInput.trim() || assets.length === 0) return;

    setUploading(true);

    try {
      // Upload files to Supabase Storage via backend
      const uploadedUrls: { url: string; description: string }[] = [];

      for (const asset of assets) {
        const formData = new FormData();
        formData.append("file", asset.file);
        formData.append("description", asset.description);

        const response = await fetch("http://127.0.0.1:8000/upload", {
          method: "POST",
          body: formData,
        });

        const data = await response.json();
        uploadedUrls.push({
          url: data.url,
          description: data.description,  // Use AI-generated description from backend
        });
      }

      // Start pipeline with uploaded assets
      onStart(userInput, uploadedUrls);
    } catch (error) {
      console.error("Upload failed:", error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white mb-2">Upload Screenshots</h2>
        <p className="text-sm text-gray-400">
          Upload your app screenshots and I'll create a promo video from them.
        </p>
      </div>

      {/* Drop Zone */}
      <div
        className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center hover:border-gray-500 transition-colors cursor-pointer"
        onClick={() => document.getElementById("file-input")?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFileSelect(e.dataTransfer.files);
        }}
      >
        <Upload className="w-8 h-8 text-gray-500 mx-auto mb-2" />
        <p className="text-gray-400">Drop images here or click to upload</p>
        <input
          id="file-input"
          type="file"
          multiple
          accept="image/*"
          className="hidden"
          onChange={(e) => handleFileSelect(e.target.files)}
        />
      </div>

      {/* Preview Grid */}
      {assets.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          {assets.map((asset, index) => (
            <div key={index} className="relative group">
              <img
                src={asset.preview}
                alt={asset.description}
                className="w-full aspect-[9/16] object-cover rounded-lg"
              />
              <button
                onClick={() => removeAsset(index)}
                className="absolute top-1 right-1 p-1 bg-red-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="w-3 h-3 text-white" />
              </button>
              <input
                type="text"
                value={asset.description}
                onChange={(e) => {
                  setAssets((prev) => {
                    const updated = [...prev];
                    updated[index].description = e.target.value;
                    return updated;
                  });
                }}
                className="absolute bottom-0 left-0 right-0 bg-black/70 text-white text-xs p-1 rounded-b-lg"
                placeholder="Description"
              />
            </div>
          ))}
        </div>
      )}

      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Video Description
        </label>
        <textarea
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          placeholder="Describe what kind of video you want..."
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm resize-none"
          rows={3}
        />
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!userInput.trim() || assets.length === 0 || uploading}
        className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
      >
        {uploading ? "Uploading..." : `Create Video from ${assets.length} Images`}
      </button>
    </div>
  );
}

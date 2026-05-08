"use client";

import { ImageUploader } from "@/components/analyze/image-uploader";
import { CameraCapture } from "@/components/analyze/camera-capture";
import { useState } from "react";
import { Camera, Upload } from "lucide-react";

export default function AnalyzePage() {
  const [mode, setMode] = useState<"upload" | "camera">("upload");

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Analyze a Dog</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload a clear photo of a dog to identify the breed and generate a personalized diet plan.
        </p>
      </div>

      {/* Mode switcher */}
      <div className="flex rounded-xl border border-border bg-muted/30 p-1">
        <button
          onClick={() => setMode("upload")}
          className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition-all ${
            mode === "upload"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Upload className="h-4 w-4" />
          Upload Image
        </button>
        <button
          onClick={() => setMode("camera")}
          className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition-all ${
            mode === "camera"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Camera className="h-4 w-4" />
          Use Camera
        </button>
      </div>

      {mode === "upload" ? <ImageUploader /> : <CameraCapture />}
    </div>
  );
}

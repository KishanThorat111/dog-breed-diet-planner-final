"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAnalyzeImage } from "@/hooks/use-predictions";
import { PredictionResult } from "./prediction-result";
import type { Prediction } from "@/types";
import { Camera, Loader2, RotateCcw } from "lucide-react";

export function CameraCapture() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [captured, setCaptured] = useState<string | null>(null);
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { mutate: analyze, isPending } = useAnalyzeImage();

  const startCamera = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        setIsStreaming(true);
      }
    } catch {
      setError("Camera access denied. Please allow camera permissions and try again.");
    }
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setIsStreaming(false);
  }, []);

  const capture = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);

    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
        const url = URL.createObjectURL(blob);
        setCaptured(url);
        stopCamera();
        setResult(null);
        analyze({ file }, { onSuccess: (data) => setResult(data) });
      },
      "image/jpeg",
      0.92
    );
  }, [analyze, stopCamera]);

  const reset = useCallback(() => {
    setCaptured(null);
    setResult(null);
    startCamera();
  }, [startCamera]);

  useEffect(() => {
    startCamera();
    return () => stopCamera();
  }, [startCamera, stopCamera]);

  if (error) {
    return (
      <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-6 text-center">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="relative overflow-hidden rounded-2xl bg-black">
        {!captured ? (
          <video
            ref={videoRef}
            className="w-full rounded-2xl"
            playsInline
            muted
          />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={captured} alt="Captured" className="w-full rounded-2xl" />
        )}
        <canvas ref={canvasRef} className="hidden" />

        {isPending && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-white" />
              <p className="text-sm font-medium text-white">Analyzing breed...</p>
            </div>
          </div>
        )}
      </div>

      {isStreaming && (
        <button
          onClick={capture}
          disabled={isPending}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-3.5 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:bg-primary/90 disabled:opacity-60"
        >
          <Camera className="h-5 w-5" />
          Capture Photo
        </button>
      )}

      {captured && !isPending && (
        <button
          onClick={reset}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-border py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted"
        >
          <RotateCcw className="h-4 w-4" />
          Retake
        </button>
      )}

      {result && <PredictionResult prediction={result} />}
    </div>
  );
}

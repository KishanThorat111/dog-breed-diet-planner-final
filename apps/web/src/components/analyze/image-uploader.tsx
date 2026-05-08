"use client";

import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useAnalyzeImage } from "@/hooks/use-predictions";
import { PredictionResult } from "./prediction-result";
import type { Prediction } from "@/types";
import { ImageIcon, Loader2, Upload } from "lucide-react";
import { ACCEPTED_IMAGE_TYPES, MAX_UPLOAD_SIZE_MB } from "@/lib/constants";
import { toast } from "sonner";

export function ImageUploader() {
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<Prediction | null>(null);
  const { mutate: analyze, isPending } = useAnalyzeImage();

  // Revoke object URL on unmount or when preview changes to avoid memory leaks
  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);

  const onDrop = useCallback(
    (accepted: File[]) => {
      const file = accepted[0];
      if (!file) return;
      if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
        toast.error(`File too large. Max ${MAX_UPLOAD_SIZE_MB}MB.`);
        return;
      }
      const url = URL.createObjectURL(file);
      setPreview(url);
      setResult(null);
      analyze({ file }, { onSuccess: (data) => setResult(data) });
    },
    [analyze]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: Object.fromEntries(ACCEPTED_IMAGE_TYPES.map((t) => [t, []])),
    maxFiles: 1,
    disabled: isPending,
  });

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`relative flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed transition-all ${
          isDragActive
            ? "border-primary bg-primary/5"
            : "border-border bg-muted/20 hover:border-primary/50 hover:bg-muted/40"
        } ${isPending ? "pointer-events-none opacity-60" : ""}`}
      >
        <input {...getInputProps()} />

        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={preview}
            alt="Preview"
            className="h-full max-h-80 w-full rounded-xl object-contain p-2"
          />
        ) : (
          <div className="flex flex-col items-center gap-3 px-4 py-8 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
              <ImageIcon className="h-7 w-7 text-muted-foreground" />
            </div>
            <div>
              <p className="font-medium text-foreground">
                {isDragActive ? "Drop the image here" : "Drag & drop an image"}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                or click to browse · JPG, PNG, WebP · max {MAX_UPLOAD_SIZE_MB}MB
              </p>
            </div>
          </div>
        )}

        {isPending && (
          <div className="absolute inset-0 flex items-center justify-center rounded-2xl bg-background/80 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm font-medium text-foreground">Analyzing breed...</p>
            </div>
          </div>
        )}
      </div>

      {preview && !isPending && !result && (
        <button
          onClick={() => { setPreview(null); setResult(null); }}
          className="w-full rounded-lg border border-border py-2.5 text-sm text-muted-foreground transition-colors hover:bg-muted"
        >
          Clear
        </button>
      )}

      {result && <PredictionResult prediction={result} />}

      {!preview && (
        <div className="flex items-center justify-center">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow-sm transition-all hover:bg-primary/90">
            <Upload className="h-4 w-4" />
            Choose Image
            <input
              type="file"
              className="hidden"
              accept={ACCEPTED_IMAGE_TYPES.join(",")}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) onDrop([file]);
              }}
            />
          </label>
        </div>
      )}
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useAnalyzeImage } from "@/hooks/use-predictions";
import { PredictionResult } from "./prediction-result";
import type { Prediction } from "@/types";
import { ImageIcon, Loader2, Upload } from "lucide-react";
import { ACCEPTED_IMAGE_TYPES, MAX_UPLOAD_SIZE_MB } from "@/lib/constants";
import { toast } from "sonner";

// ─── Client-side compression ──────────────────────────────────────────────────
// Compresses an image to JPEG at the given quality without perceptible quality
// loss. Typical smartphone photos (4-8 MB) compress to 300-800 KB at 88%.
// Max dimension is capped at 1920 px so that the server never receives an
// overly large decode surface.
async function compressImage(
  file: File,
  maxDimension = 1920,
  quality = 0.88
): Promise<File> {
  // Skip tiny files — compression overhead not worth it
  if (file.size < 200 * 1024) return file;

  return new Promise((resolve, reject) => {
    const img = new Image();
    const objectUrl = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(objectUrl);

      let { width, height } = img;
      if (width > maxDimension || height > maxDimension) {
        const ratio = Math.min(maxDimension / width, maxDimension / height);
        width = Math.round(width * ratio);
        height = Math.round(height * ratio);
      }

      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) return resolve(file); // Fallback: send original
      ctx.drawImage(img, 0, 0, width, height);

      canvas.toBlob(
        (blob) => {
          if (!blob) return resolve(file);
          const compressed = new File(
            [blob],
            file.name.replace(/\.[^.]+$/, ".jpg"),
            { type: "image/jpeg" }
          );
          // Only use compressed version if it's actually smaller
          resolve(compressed.size < file.size ? compressed : file);
        },
        "image/jpeg",
        quality
      );
    };

    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(file); // Fallback: send original
    };

    img.src = objectUrl;
  });
}
// ─────────────────────────────────────────────────────────────────────────────

export function ImageUploader() {
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<Prediction | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);
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
    async (accepted: File[]) => {
      const file = accepted[0];
      if (!file) return;
      if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
        toast.error(`File too large. Max ${MAX_UPLOAD_SIZE_MB}MB.`);
        return;
      }

      // Show preview immediately with original file
      const url = URL.createObjectURL(file);
      setPreview(url);
      setResult(null);

      // Compress before upload
      setIsCompressing(true);
      let fileToUpload = file;
      try {
        fileToUpload = await compressImage(file);
        if (fileToUpload !== file) {
          const savedKB = Math.round((file.size - fileToUpload.size) / 1024);
          if (savedKB > 10) {
            toast.success(`Image compressed — saved ${savedKB} KB`, { duration: 2000 });
          }
        }
      } catch {
        // Compression failed silently — use original
        fileToUpload = file;
      } finally {
        setIsCompressing(false);
      }

      analyze(
        { file: fileToUpload },
        {
          onSuccess: (data) => setResult(data),
          onError: (err: Error) => {
            // Show clear error for non-dog images; generic for other failures
            const msg = err.message || "";
            if (msg.toLowerCase().includes("no dog")) {
              toast.error("No dog detected. Please upload a clear photo of a dog.", { duration: 5000 });
            } else {
              toast.error(msg || "Analysis failed. Please try again.");
            }
            setPreview(null);
          },
        }
      );
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
              <p className="text-sm font-medium text-foreground">
                {isCompressing ? "Compressing image..." : "Analyzing breed..."}
              </p>
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

"use client";

/**
 * FileUpload.tsx — Drag-and-drop multi-PDF upload component.
 *
 * Features:
 *   - Drag-and-drop zone (multiple files) with visual feedback.
 *   - Click-to-browse file picker (PDF only, multiple selection).
 *   - Real-time aggregate upload progress bar.
 *   - Success / error status display.
 */

import React, { useCallback, useRef, useState } from "react";
import {
  uploadDocuments,
  type DocumentResponse,
} from "@/lib/api";

interface FileUploadProps {
  /** Called after files are successfully uploaded. */
  onUploadComplete: (docs: DocumentResponse[]) => void;
}

export default function FileUpload({ onUploadComplete }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ── Handlers ─────────────────────────────────────────────────────────

  const handleFiles = useCallback(
    async (fileList: FileList | File[]) => {
      const files = Array.from(fileList).filter((f) =>
        f.name.toLowerCase().endsWith(".pdf"),
      );
      const rejected = Array.from(fileList).length - files.length;

      if (files.length === 0) {
        setError("Only PDF files are accepted.");
        return;
      }

      setError(null);
      setSuccess(null);
      setStatusText("");
      setIsUploading(true);
      setProgress(0);

      try {
        const { uploaded: docs, errors } = await uploadDocuments(files, (pct, msg) => {
          setProgress(pct);
          setStatusText(msg);
        });

        if (docs.length > 0) {
          setSuccess(
            `${docs.length} file${docs.length > 1 ? "s" : ""} uploaded — processing…` +
              (rejected > 0
                ? ` (${rejected} non-PDF file${rejected > 1 ? "s" : ""} skipped)`
                : ""),
          );
          onUploadComplete(docs);
        }
        if (errors.length > 0) {
          setError(`Some uploads failed — ${errors.join("; ")}`);
        }
      } catch {
        setError("Upload failed unexpectedly.");
      } finally {
        setIsUploading(false);
        setStatusText("");
      }
    },
    [onUploadComplete],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) handleFiles(files);
    },
    [handleFiles],
  );

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) handleFiles(files);
      // Reset so the same files can be re-selected.
      e.target.value = "";
    },
    [handleFiles],
  );

  // ── Render ───────────────────────────────────────────────────────────

  return (
    <div className="mb-4">
      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        className={`
          flex flex-col items-center justify-center gap-2
          rounded-xl border-2 border-dashed p-6
          cursor-pointer transition-all duration-200
          ${
            isDragging
              ? "border-indigo-400 bg-indigo-500/10"
              : "border-slate-600 hover:border-indigo-500/50 hover:bg-slate-800/50"
          }
        `}
      >
        {/* Icon */}
        <svg
          className="h-8 w-8 text-slate-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 16V4m0 0l-4 4m4-4l4 4M4 18h16"
          />
        </svg>
        <p className="text-sm text-slate-400">
          {isUploading
            ? "Uploading…"
            : "Drag & drop PDFs here, or click to browse"}
        </p>

        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={onFileChange}
        />
      </div>

      {/* Progress bar */}
      {isUploading && (
        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-[10px] text-slate-500">
            <span className="truncate">{statusText}</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-700">
            <div
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Success / Error messages */}
      {success && (
        <p className="mt-2 text-xs text-emerald-400">{success}</p>
      )}
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </div>
  );
}

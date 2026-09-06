"use client";

/**
 * DocumentList.tsx — Sidebar list of uploaded documents.
 *
 * Shows each document with a status badge and a delete button.
 * Documents can be toggled on/off to control which ones are included
 * in the RAG search scope.
 */

import React from "react";
import type { DocumentResponse } from "@/lib/api";

interface DocumentListProps {
  /** All known documents. */
  documents: DocumentResponse[];
  /** Currently selected document IDs. */
  selectedIds: Set<string>;
  /** Toggle a document's selection state. */
  onToggle: (id: string) => void;
  /** Delete a document. */
  onDelete: (id: string) => void;
}

/** Map document status to badge colour classes. */
const STATUS_STYLES: Record<string, string> = {
  processing: "bg-amber-500/20 text-amber-400",
  completed: "bg-emerald-500/20 text-emerald-400",
  failed: "bg-red-500/20 text-red-400",
};

export default function DocumentList({
  documents,
  selectedIds,
  onToggle,
  onDelete,
}: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <p className="px-2 py-4 text-center text-xs text-slate-500">
        No documents uploaded yet.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-1.5">
      {documents.map((doc) => {
        const isSelected = selectedIds.has(doc.id);
        return (
          <li
            key={doc.id}
            className={`
              group flex items-center gap-2 rounded-lg px-3 py-2
              cursor-pointer transition-all duration-150
              ${
                isSelected
                  ? "bg-indigo-500/15 ring-1 ring-indigo-500/40"
                  : "hover:bg-slate-800/60"
              }
            `}
            onClick={() => onToggle(doc.id)}
          >
            {/* Checkbox */}
            <span
              className={`
                flex h-4 w-4 shrink-0 items-center justify-center rounded
                border transition-colors
                ${
                  isSelected
                    ? "border-indigo-500 bg-indigo-500"
                    : "border-slate-600"
                }
              `}
            >
              {isSelected && (
                <svg
                  className="h-3 w-3 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={3}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              )}
            </span>

            {/* Filename + status */}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-200">
                {doc.filename}
              </p>
              <div className="mt-0.5 flex items-center gap-2">
                <span
                  className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                    STATUS_STYLES[doc.status] ?? STATUS_STYLES.processing
                  }`}
                >
                  {doc.status}
                </span>
                {doc.page_count > 0 && (
                  <span className="text-[10px] text-slate-500">
                    {doc.page_count} pages
                  </span>
                )}
                {doc.chunk_count > 0 && (
                  <span className="text-[10px] text-slate-600">
                    · {doc.chunk_count} chunks
                  </span>
                )}
              </div>
            </div>

            {/* Delete button — visible on hover */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(doc.id);
              }}
              className="
                shrink-0 rounded p-1 text-slate-500
                opacity-0 transition-opacity
                hover:bg-red-500/20 hover:text-red-400
                group-hover:opacity-100
              "
              title="Delete document"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

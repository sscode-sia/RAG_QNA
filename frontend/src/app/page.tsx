"use client";

/**
 * page.tsx — Main application page.
 *
 * Two-panel layout:
 *   LEFT  — Sidebar with document upload + document list.
 *   RIGHT — Chat interface for Q&A.
 *
 * State flows:
 *   1. User uploads a PDF → appears in sidebar with "processing" badge.
 *   2. Polling refreshes the list → badge turns "completed" when ready.
 *   3. User selects documents → only those are included in queries.
 *   4. User asks a question → answer with citations appears in the chat.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import FileUpload from "@/components/FileUpload";
import DocumentList from "@/components/DocumentList";
import ChatInterface from "@/components/ChatInterface";
import UsagePanel from "@/components/UsagePanel";
import {
  getDocuments,
  getStats,
  deleteDocument as apiDeleteDocument,
  type DocumentResponse,
  type UsageStats,
} from "@/lib/api";

export default function HomePage() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [stats, setStats] = useState<UsageStats | null>(null);
  const statsVersionRef = useRef(0);

  // ── Fetch documents on mount + poll only while a doc is processing ─────

  const refreshDocuments = useCallback(async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch {
      // Silently ignore — backend may not be running yet.
    }
  }, []);

  const refreshStats = useCallback(async () => {
    // Bump version so in-flight responses from older calls are discarded.
    const version = ++statsVersionRef.current;
    try {
      const s = await getStats();
      if (statsVersionRef.current === version) setStats(s);
    } catch {
      // Backend may not be running yet.
    }
  }, []);

  // Poll documents only while at least one is still processing.
  const hasProcessing = documents.some((d) => d.status === "processing");
  useEffect(() => {
    if (!hasProcessing) return;
    const interval = setInterval(refreshDocuments, 3000);
    return () => clearInterval(interval);
  }, [hasProcessing, refreshDocuments]);

  // Load documents + stats once on mount.
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const docs = await getDocuments();
        if (!cancelled) setDocuments(docs);
      } catch {
        // Backend may not be running yet.
      }
    };
    const loadStats = async () => {
      try {
        const s = await getStats();
        if (!cancelled) setStats(s);
      } catch {
        // Backend may not be running yet.
      }
    };
    load();
    loadStats();
    return () => {
      cancelled = true;
    };
  }, []);

  // ── Handlers ──────────────────────────────────────────────────────────

  const handleUploadComplete = useCallback(
    (docs: DocumentResponse[]) => {
      if (docs.length > 0) {
        setDocuments((prev) => [...docs, ...prev]);
        // Auto-select newly uploaded documents.
        setSelectedIds((prev) => new Set([...prev, ...docs.map((d) => d.id)]));
      }
      // Stats (doc/chunk counts) changed — refresh.
      refreshStats();
    },
    [refreshStats],
  );

  const handleToggle = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await apiDeleteDocument(id);
        setDocuments((prev) => prev.filter((d) => d.id !== id));
        setSelectedIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        refreshStats();
      } catch (err) {
        console.error("Failed to delete document:", err);
      }
    },
    [refreshStats],
  );

  // Called by ChatInterface after each answer so token totals update live.
  const handleQueryAnswered = useCallback(() => {
    refreshStats();
  }, [refreshStats]);

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen">
      {/* ── Sidebar ──────────────────────────────────────────────────── */}
      <aside className="flex w-80 shrink-0 flex-col border-r border-slate-800 bg-slate-950">
        {/* Brand header */}
        <div className="flex items-center gap-2.5 border-b border-slate-800 px-5 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600">
            <svg
              className="h-4 w-4 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-white">
              DocQ&A
            </h1>
            <p className="text-[10px] text-slate-500">
              AI-Powered Document Q&A
            </p>
          </div>
        </div>

        {/* Upload area */}
        <div className="border-b border-slate-800 px-4 py-4">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Upload Document
          </h2>
          <FileUpload onUploadComplete={handleUploadComplete} />
        </div>

        {/* Document list */}
        <div className="flex-1 overflow-y-auto px-3 py-3">
          <h2 className="mb-2 px-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Documents
            {documents.length > 0 && (
              <span className="ml-1.5 text-slate-600">({documents.length})</span>
            )}
          </h2>
          <DocumentList
            documents={documents}
            selectedIds={selectedIds}
            onToggle={handleToggle}
            onDelete={handleDelete}
          />
        </div>

        {/* Selected summary */}
        {selectedIds.size > 0 && (
          <div className="border-t border-slate-800 px-4 py-2.5">
            <p className="text-[11px] text-slate-500">
              <span className="font-semibold text-indigo-400">
                {selectedIds.size}
              </span>{" "}
              document{selectedIds.size > 1 ? "s" : ""} selected for Q&A
            </p>
          </div>
        )}

        {/* Usage / token stats */}
        <UsagePanel stats={stats} />
      </aside>

      {/* ── Main chat area ───────────────────────────────────────────── */}
      <main className="flex flex-1 flex-col bg-slate-900">
        <ChatInterface
          activeDocumentIds={Array.from(selectedIds)}
          onQueryAnswered={handleQueryAnswered}
        />
      </main>
    </div>
  );
}

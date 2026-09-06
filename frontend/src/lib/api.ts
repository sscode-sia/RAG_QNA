/**
 * api.ts — HTTP client for the backend REST API.
 *
 * All functions point at the FastAPI server (default: http://localhost:8000).
 * Each function maps 1-to-1 to a backend endpoint and returns typed data.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

// ── Types ────────────────────────────────────────────────────────────────────

/** Mirrors backend `DocumentResponse`. */
export interface DocumentResponse {
  id: string;
  filename: string;
  status: "processing" | "completed" | "failed";
  upload_time: string | null;
  page_count: number;
  chunk_count: number;
}

/** Mirrors backend `Citation`. */
export interface Citation {
  document_id: string;
  filename: string;
  page_number: number;
  text_snippet: string;
}

/** Mirrors backend `TokenUsage`. */
export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

/** Mirrors backend `QueryResponse`. */
export interface QueryResponse {
  answer: string;
  citations: Citation[];
  usage: TokenUsage;
  latency_ms: number;
  contributing_docs: string[];
}

/** Mirrors backend `UsageStats`. */
export interface UsageStats {
  total_queries: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  avg_latency_ms: number;
  documents: number;
  vectors_stored: number;
}

// ── API Functions ────────────────────────────────────────────────────────────

/**
 * Upload a PDF file to the backend.
 *
 * @param file      - The PDF `File` object from a file input or drop event.
 * @param onProgress - Optional callback receiving upload percentage (0–100).
 * @returns The created `DocumentResponse` with status `"processing"`.
 */
export async function uploadDocument(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<DocumentResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.open("POST", `${API_BASE}/upload`);
    xhr.timeout = 120_000;

    // Track upload progress
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && onProgress) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new Error("Invalid response from server"));
        }
      } else {
        let detail = "";
        try {
          const body = JSON.parse(xhr.responseText);
          detail = body.detail ?? body.message ?? "";
        } catch {
          detail = xhr.responseText.slice(0, 200);
        }
        reject(
          new Error(detail || `Upload failed (HTTP ${xhr.status})`),
        );
      }
    });

    xhr.addEventListener("error", () =>
      reject(
        new Error(
          "Network error — server unreachable. Is the backend running on port 8000?",
        ),
      ),
    );
    xhr.addEventListener("timeout", () =>
      reject(new Error("Upload timed out")),
    );
    xhr.send(formData);
  });
}

/**
 * Upload multiple PDFs sequentially.
 *
 * Files are sent one at a time to keep each request small and let the
 * backend ingest them in parallel background tasks.
 *
 * @param files      - The PDF `File` objects to upload.
 * @param onProgress - Optional callback receiving overall percentage (0–100)
 *                     across all files, and the per-file progress message.
 * @returns The created `DocumentResponse` objects (failed uploads are skipped).
 */
export async function uploadDocuments(
  files: File[],
  onProgress?: (percent: number, message: string) => void,
): Promise<{ uploaded: DocumentResponse[]; errors: string[] }> {
  const uploaded: DocumentResponse[] = [];
  const errors: string[] = [];

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    try {
      const doc = await uploadDocument(file, (pct) => {
        // Weight per-file progress by its share of the total.
        const overall = Math.round(
          ((i + pct / 100) / files.length) * 100,
        );
        onProgress?.(overall, `${file.name} (${i + 1}/${files.length})`);
      });
      uploaded.push(doc);
    } catch (err: unknown) {
      errors.push(
        `${file.name}: ${err instanceof Error ? err.message : "upload failed"}`,
      );
    }
  }

  return { uploaded, errors };
}

/**
 * Send a natural-language query to the RAG pipeline.
 *
 * @param query       - The user's question.
 * @param documentIds - UUIDs of documents to search within (empty = all).
 * @returns The LLM answer with structured citations.
 */
export async function queryDocuments(
  query: string,
  documentIds: string[] = [],
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, document_ids: documentIds }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Query failed (${res.status})`);
  }

  return res.json();
}

/**
 * Fetch the list of all uploaded documents.
 */
export async function getDocuments(): Promise<DocumentResponse[]> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error(`Failed to fetch documents (${res.status})`);
  return res.json();
}

/**
 * Delete a document and its vectors from the backend.
 *
 * @param docId - UUID of the document to remove.
 */
export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${docId}`, {
    method: "DELETE",
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`Failed to delete document (${res.status})`);
  }
}

/**
 * Fetch aggregated usage & token statistics.
 */
export async function getStats(): Promise<UsageStats> {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error(`Failed to fetch stats (${res.status})`);
  return res.json();
}

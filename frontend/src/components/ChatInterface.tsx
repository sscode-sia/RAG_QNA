"use client";

/**
 * ChatInterface.tsx — Conversational Q&A interface.
 *
 * Renders a scrollable message feed (user questions + AI answers) and an
 * input bar at the bottom.  AI answers contain inline citation tags that are
 * parsed and rendered as styled badges.
 */

import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import remarkGfm from "remark-gfm";
import {
  queryDocuments,
  type Citation,
  type QueryResponse,
  type TokenUsage,
} from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  usage?: TokenUsage;
  latencyMs?: number;
  contributingDocs?: string[];
  timestamp: Date;
}

interface ChatInterfaceProps {
  /** Active document IDs to include in the query scope. */
  activeDocumentIds: string[];
  /** Called after each answer so the parent can refresh usage stats. */
  onQueryAnswered?: () => void;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Replace `[Doc: X, Page: Y]` citation tags with styled HTML badges. */
function injectCitationBadges(text: string): string {
  return text.replace(
    /\[Doc:\s*(.+?),\s*Page:\s*(\d+)\]/g,
    '<cite class="cite-badge">$1 · p.$2</cite>',
  );
}

/** Custom markdown components styled for the dark chat UI. */
const markdownComponents = {
  h1: ({ children, ...props }: React.ComponentProps<"h1">) => (
    <h1 className="mb-2 mt-3 text-lg font-bold text-white" {...props}>{children}</h1>
  ),
  h2: ({ children, ...props }: React.ComponentProps<"h2">) => (
    <h2 className="mb-2 mt-3 text-base font-bold text-white" {...props}>{children}</h2>
  ),
  h3: ({ children, ...props }: React.ComponentProps<"h3">) => (
    <h3 className="mb-1.5 mt-2.5 text-sm font-bold text-white" {...props}>{children}</h3>
  ),
  p: ({ children, ...props }: React.ComponentProps<"p">) => (
    <p className="mb-2 last:mb-0" {...props}>{children}</p>
  ),
  ul: ({ children, ...props }: React.ComponentProps<"ul">) => (
    <ul className="mb-2 ml-4 list-disc space-y-1" {...props}>{children}</ul>
  ),
  ol: ({ children, ...props }: React.ComponentProps<"ol">) => (
    <ol className="mb-2 ml-4 list-decimal space-y-1" {...props}>{children}</ol>
  ),
  li: ({ children, ...props }: React.ComponentProps<"li">) => (
    <li className="leading-relaxed" {...props}>{children}</li>
  ),
  strong: ({ children, ...props }: React.ComponentProps<"strong">) => (
    <strong className="font-semibold text-white" {...props}>{children}</strong>
  ),
  code: ({ children, className, ...props }: React.ComponentProps<"code">) => {
    const isBlock = className?.includes("language-");
    return isBlock ? (
      <code className={`block overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-emerald-300 ${className ?? ""}`} {...props}>
        {children}
      </code>
    ) : (
      <code className="rounded bg-slate-700 px-1 py-0.5 text-xs text-emerald-300" {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children, ...props }: React.ComponentProps<"pre">) => (
    <pre className="mb-2 overflow-x-auto" {...props}>{children}</pre>
  ),
  blockquote: ({ children, ...props }: React.ComponentProps<"blockquote">) => (
    <blockquote className="mb-2 border-l-2 border-indigo-500 pl-3 italic text-slate-400" {...props}>
      {children}
    </blockquote>
  ),
  table: ({ children, ...props }: React.ComponentProps<"table">) => (
    <div className="mb-2 overflow-x-auto">
      <table className="min-w-full text-xs" {...props}>{children}</table>
    </div>
  ),
  th: ({ children, ...props }: React.ComponentProps<"th">) => (
    <th className="border border-slate-600 bg-slate-800 px-2 py-1 text-left font-semibold text-white" {...props}>{children}</th>
  ),
  td: ({ children, ...props }: React.ComponentProps<"td">) => (
    <td className="border border-slate-700 px-2 py-1" {...props}>{children}</td>
  ),
  hr: (props: React.ComponentProps<"hr">) => (
    <hr className="my-3 border-slate-700" {...props} />
  ),
};

/** Render assistant message content with markdown formatting + citation badges. */
function renderMessageContent(content: string): React.ReactNode {
  // First, convert citation tags to HTML badges
  const processed = injectCitationBadges(content);

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw]}
      components={markdownComponents}
    >
      {processed}
    </ReactMarkdown>
  );
}

// ── Component ────────────────────────────────────────────────────────────────

export default function ChatInterface({
  activeDocumentIds,
  onQueryAnswered,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      const query = input.trim();
      if (!query || isLoading) return;

      // Add user message
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: query,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsLoading(true);

      try {
        const response: QueryResponse = await queryDocuments(
          query,
          activeDocumentIds,
        );

        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          citations: response.citations,
          usage: response.usage,
          latencyMs: response.latency_ms,
          contributingDocs: response.contributing_docs,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err: unknown) {
        const errMsg =
          err instanceof Error ? err.message : "Something went wrong.";
        const errorAssistantMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `⚠️ Error: ${errMsg}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorAssistantMsg]);
      } finally {
        setIsLoading(false);
        onQueryAnswered?.();
      }
    },
    [input, isLoading, activeDocumentIds, onQueryAnswered],
  );

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div className="flex h-full flex-col">
      {/* Message feed */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-slate-500">
            <svg className="h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
              />
            </svg>
            <p className="text-sm">Upload a document, then ask a question.</p>
          </div>
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-6">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`
                    max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed
                    ${
                      msg.role === "user"
                        ? "bg-indigo-600 text-white"
                        : "bg-slate-800 text-slate-200 ring-1 ring-slate-700"
                    }
                  `}
                >
                  {/* Message body */}
                  <div>
                    {msg.role === "assistant"
                      ? renderMessageContent(msg.content)
                      : msg.content}
                  </div>

                  {/* Expandable citations panel */}
                  {msg.role === "assistant" && msg.citations && msg.citations.length > 0 && (
                    <details className="mt-3 border-t border-slate-700 pt-2">
                      <summary className="cursor-pointer text-xs font-medium text-indigo-400 hover:text-indigo-300">
                        {msg.citations.length} source{msg.citations.length > 1 ? "s" : ""}
                      </summary>
                      <ul className="mt-2 flex flex-col gap-1.5">
                        {msg.citations.map((cite, i) => (
                          <li
                            key={i}
                            className="rounded-lg bg-slate-900/60 p-2 text-xs text-slate-400"
                          >
                            <span className="font-semibold text-slate-300">
                              {cite.filename} — Page {cite.page_number}
                            </span>
                            {cite.text_snippet && (
                              <p className="mt-1 line-clamp-2 italic text-slate-500">
                                &ldquo;{cite.text_snippet}&rdquo;
                              </p>
                            )}
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}

                  {/* Token usage / latency footer */}
                  {msg.role === "assistant" && (msg.usage || msg.latencyMs) && (
                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-slate-700 pt-1.5 text-[10px] text-slate-500">
                      {msg.usage && msg.usage.total_tokens > 0 && (
                        <span title="Prompt (in) + completion (out) tokens">
                          <span className="text-slate-400">tokens:</span>{" "}
                          {msg.usage.total_tokens.toLocaleString()}
                          <span className="ml-1 text-slate-600">
                            ({msg.usage.prompt_tokens.toLocaleString()} in /{" "}
                            {msg.usage.completion_tokens.toLocaleString()} out)
                          </span>
                        </span>
                      )}
                      {msg.latencyMs != null && msg.latencyMs > 0 && (
                        <span>
                          <span className="text-slate-400">latency:</span>{" "}
                          {(msg.latencyMs / 1000).toFixed(1)}s
                        </span>
                      )}
                      {msg.contributingDocs &&
                        msg.contributingDocs.length > 0 && (
                          <span
                            title="Documents that supplied context for this answer"
                            className="max-w-full truncate"
                          >
                            <span className="text-slate-400">from:</span>{" "}
                            {msg.contributingDocs.join(", ")}
                          </span>
                        )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-2xl bg-slate-800 px-4 py-3 ring-1 ring-slate-700">
                  <div className="flex gap-1">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-indigo-400 [animation-delay:0ms]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-indigo-400 [animation-delay:150ms]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-indigo-400 [animation-delay:300ms]" />
                  </div>
                  <span className="text-xs text-slate-400">Thinking…</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t border-slate-800 bg-slate-950/80 px-4 py-3 backdrop-blur-sm">
        <form
          onSubmit={handleSubmit}
          className="mx-auto flex max-w-3xl items-end gap-2"
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder={
              activeDocumentIds.length > 0
                ? "Ask a question about your documents…"
                : "Upload a document first to start asking questions"
            }
            disabled={isLoading}
            rows={1}
            className="
              flex-1 resize-none rounded-xl border border-slate-700
              bg-slate-900 px-4 py-2.5 text-sm text-slate-200
              placeholder:text-slate-500
              focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500
              disabled:cursor-not-allowed disabled:opacity-50
            "
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="
              flex h-10 w-10 shrink-0 items-center justify-center
              rounded-xl bg-indigo-600 text-white
              transition-colors
              hover:bg-indigo-500
              disabled:cursor-not-allowed disabled:opacity-40
            "
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M14 5l7 7m0 0l-7 7m7-7H3"
              />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}

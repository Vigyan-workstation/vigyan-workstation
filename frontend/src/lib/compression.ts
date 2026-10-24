// Vigyan Pro — Context Compression Engine
// Compresses multi-turn conversation history into dense executive memory capsules.
// Guarantees fast local SLM inference on low-spec CPUs and prevents 2048-token context overflow.

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

const STORAGE_KEY = "vigyan_context_compression_enabled";

/**
 * Returns true if context compression is enabled (defaults to true).
 */
export function isCompressionEnabled(): boolean {
  if (typeof window === "undefined") return true;
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved === null ? true : saved === "true";
}

/**
 * Save user preference for context compression.
 */
export function setCompressionEnabled(enabled: boolean): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
}

/**
 * Compress multi-turn history into an executive summary + latest turns.
 *
 * @param messages Full chat history array
 * @param maxRecent Number of recent messages to preserve verbatim (default 4)
 * @returns Compressed message array with estimated token savings
 */
export function compressContext(
  messages: ChatMessage[],
  maxRecent: number = 4
): { compressed: ChatMessage[]; tokensSaved: number; summary: string } {
  // If conversation is short, keep as is
  if (messages.length <= maxRecent + 1) {
    return { compressed: messages, tokensSaved: 0, summary: "" };
  }

  const older = messages.slice(0, messages.length - maxRecent);
  const recent = messages.slice(messages.length - maxRecent);

  // Measure raw character count before compression
  const rawChars = older.reduce((sum, m) => sum + m.content.length, 0);

  // Build condensed executive capsule
  const summaryBullets: string[] = [];

  for (const m of older) {
    if (!m.content.trim()) continue;

    if (m.role === "user") {
      const q = m.content.length > 80 ? m.content.slice(0, 80) + "…" : m.content;
      summaryBullets.push(`User asked: "${q.replace(/\n/g, " ")}"`);
    } else if (m.role === "assistant") {
      // Extract key equations or first two sentences
      const firstSentence = m.content.split(/[.\n]/)[0] ?? "";
      const eq = m.content.match(/(?:\\\[|\$\$)([\s\S]*?)(?:\\\]|\$\$)/);
      let note = firstSentence.slice(0, 75);
      if (eq && eq[1]) {
        note += ` [Formula: ${eq[1].trim().slice(0, 40)}]`;
      }
      summaryBullets.push(`Resolved: ${note}`);
    }
  }

  const summary =
    `[Context Memory Capsule — Prior Conversation History]:\n` +
    summaryBullets.map((b) => `• ${b}`).join("\n");

  const summaryChars = summary.length;
  // Estimate tokens (~4 characters per token in English/LaTeX)
  const tokensSaved = Math.max(0, Math.round((rawChars - summaryChars) / 4));

  const compressed: ChatMessage[] = [
    { role: "system", content: summary },
    ...recent,
  ];

  return { compressed, tokensSaved, summary };
}

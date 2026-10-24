// Vigyan Pro — Chat Reactive Store (Svelte 5 Runes)
// Handles chat messages, local persistence in localStorage, and context compression.

import { compressContext } from "./compression";
import type { ToolResult } from "./ollama";

export interface Attachment {
  name: string;
  size: number;
  type: "image" | "document";
  dataUrl?: string;
}

export interface Digest {
  filename: string;
  summary: string;
  metrics: string[];
  actions: string[];
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  thinking: string;
  thinkingDone: boolean;
  streaming: boolean;
  sympyGrounding?: string;
  toolResults?: ToolResult[];
  attachment?: Attachment;
  digest?: Digest;
}

const STORAGE_KEY = "vigyan_chat_history";

function loadFromStorage(): Message[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveToStorage(msgs: Message[]) {
  if (typeof window === "undefined") return;
  try {
    const persistent = msgs.filter((m) => !m.streaming || m.content);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(persistent));
  } catch {
    // Ignore storage quota errors
  }
}

class ChatStore {
  messages = $state<Message[]>(loadFromStorage());

  save() {
    saveToStorage(this.messages);
  }

  clear() {
    this.messages = [];
    if (typeof window !== "undefined") {
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  compress(): { tokensSaved: number; count: number; olderCount: number } {
    if (this.messages.length <= 4) return { tokensSaved: 0, count: this.messages.length, olderCount: 0 };

    const olderCount = this.messages.length - 4;
    const rawTurns = this.messages.map((m) => ({ role: m.role, content: m.content }));
    const { tokensSaved, summary } = compressContext(rawTurns, 4);

    if (summary) {
      const recent = this.messages.slice(-4);
      this.messages = [
        {
          id: Math.random().toString(36).slice(2, 10),
          role: "assistant",
          content: summary,
          thinking: `Compressed ${olderCount} older turn${olderCount !== 1 ? 's' : ''} into an executive memory summary capsule.`,
          thinkingDone: true,
          streaming: false,
        },
        ...recent,
      ];
      this.save();
      return { tokensSaved, count: this.messages.length, olderCount };
    }

    return { tokensSaved: 0, count: this.messages.length, olderCount: 0 };
  }
}

export const chatStore = new ChatStore();

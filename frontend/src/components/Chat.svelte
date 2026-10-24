<script lang="ts">
  // Chat.svelte — Sovereign Centered Reading Workspace with Floating Bottom Input
  // Obsidian Titanium monochrome styling inspired by Steve Jobs Apple typography.
  import { onMount } from "svelte";
  import { streamChat, DEFAULT_MODEL, getAgentHost, getVigyanToken } from "../lib/ollama";
  import { chatStore } from "../lib/chatStore.svelte";
  import ThinkingBlock from "./ThinkingBlock.svelte";
  import MessageBubble from "./MessageBubble.svelte";

  interface Props {
    model: string;
    fontSize: "sm" | "md" | "lg";
  }
  let { model, fontSize }: Props = $props();

  let input = $state("");
  let isStreaming = $state(false);
  let abortController: AbortController | null = null;
  let scrollEl: HTMLElement | null = null;
  let textareaEl: HTMLTextAreaElement | null = $state(null);
  let fileInputEl: HTMLInputElement | null = $state(null);
  let isDragging = $state(false);

  onMount(() => {
    scrollToBottom();
  });

  function autoResize() {
    if (!textareaEl) return;
    textareaEl.style.height = "auto";
    textareaEl.style.height = Math.min(textareaEl.scrollHeight, 140) + "px";
  }

  const STARTERS = [
    { icon: "⬡", label: "3D CAD Enclosure", prompt: "Generate a 3D electronics enclosure 140x90x35mm with 2.5mm walls." },
    { icon: "∫", label: "Solve Equation", prompt: "Solve x² + x − 12 = 0 with step-by-step derivation." },
    { icon: "⚡", label: "KiCad PCB", prompt: "Generate KiCad PCB netlist for a 555 timer astable multivibrator." },
    { icon: "📈", label: "Plot Oscillation", prompt: "Plot the damped oscillation exp(-0.15*x)*cos(2*x) from 0 to 25." },
  ];

  function handleFileDrop(e: DragEvent) {
    e.preventDefault();
    isDragging = false;
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      processIngestedFile(files[0]);
    }
  }

  function handleFileInputChange(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      processIngestedFile(input.files[0]);
    }
  }

  async function processIngestedFile(file: File) {
    const isImage = file.type.startsWith("image/") || /\.(png|jpe?g|webp|bmp|gif)$/i.test(file.name);
    const isPDF = file.type === "application/pdf" || file.name.endsWith(".pdf");

    if (isImage) {
      // Read as Data URL for clean thumbnail preview (never dump raw binary into text!)
      const reader = new FileReader();
      reader.onload = async () => {
        const dataUrl = String(reader.result || "");
        const base64 = dataUrl.split(",")[1] || "";

        chatStore.messages.push({
          id: uid(),
          role: "user",
          content: `Ingested image '${file.name}' for sovereign engineering analysis.`,
          thinking: "",
          thinkingDone: true,
          streaming: false,
          attachment: {
            name: file.name,
            size: file.size,
            type: "image",
            dataUrl,
          },
        });
        chatStore.save();
        scrollToBottom();

        // Call backend CPU OCR engine
        try {
          const host = getAgentHost();
          const token = getVigyanToken();
          const headers: Record<string, string> = { "Content-Type": "application/json" };
          if (token) headers["X-Vigyan-Token"] = token;

          const res = await fetch(`${host}/api/ingest/file`, {
            method: "POST",
            headers,
            body: JSON.stringify({
              filename: file.name,
              image_base64: base64,
            }),
          });

          if (res.ok) {
            const data = await res.json();
            chatStore.messages.push({
              id: uid(),
              role: "assistant",
              content: data.text || "Image processed via Sovereign Native OCR.",
              thinking: "Executed local CPU Tesseract OCR engine with zero cloud telemetry.\n",
              thinkingDone: true,
              streaming: false,
              digest: {
                filename: file.name,
                summary: data.summary || "Extracted engineering parameters from image.",
                metrics: data.metrics || [],
                actions: data.suggested_actions || ["Synthesize 3D CAD Enclosure", "Evaluate Mathematical Proof"],
              },
            });
            chatStore.save();
            scrollToBottom();
          }
        } catch (err) {
          console.error("OCR Ingest error:", err);
        }
      };
      reader.readAsDataURL(file);

    } else if (isPDF) {
      const reader = new FileReader();
      reader.onload = async () => {
        const dataUrl = String(reader.result || "");
        const base64 = dataUrl.split(",")[1] || "";

        chatStore.messages.push({
          id: uid(),
          role: "user",
          content: `Ingested datasheet '${file.name}' for specification extraction.`,
          thinking: "",
          thinkingDone: true,
          streaming: false,
          attachment: {
            name: file.name,
            size: file.size,
            type: "document",
          },
        });
        chatStore.save();
        scrollToBottom();

        try {
          const host = getAgentHost();
          const token = getVigyanToken();
          const headers: Record<string, string> = { "Content-Type": "application/json" };
          if (token) headers["X-Vigyan-Token"] = token;

          const res = await fetch(`${host}/api/ingest/file`, {
            method: "POST",
            headers,
            body: JSON.stringify({
              filename: file.name,
              pdf_base64: base64,
            }),
          });

          if (res.ok) {
            const data = await res.json();
            chatStore.messages.push({
              id: uid(),
              role: "assistant",
              content: data.text || "Document processed via Sovereign PDF Parser.",
              thinking: "Extracted document structure and parameters via offline parser.\n",
              thinkingDone: true,
              streaming: false,
              digest: {
                filename: file.name,
                summary: data.summary || "Extracted document specifications.",
                metrics: data.metrics || [],
                actions: data.suggested_actions || ["Synthesize 3D CAD Enclosure", "Generate KiCad PCB Netlist"],
              },
            });
            chatStore.save();
            scrollToBottom();
          }
        } catch (err) {
          console.error("PDF Ingest error:", err);
        }
      };
      reader.readAsDataURL(file);

    } else {
      // Plain text, CSV, Python, KiCad files
      const reader = new FileReader();
      reader.onload = async () => {
        const content = String(reader.result || "");
        chatStore.messages.push({
          id: uid(),
          role: "user",
          content: `Ingested document '${file.name}'.`,
          thinking: "",
          thinkingDone: true,
          streaming: false,
          attachment: {
            name: file.name,
            size: file.size,
            type: "document",
          },
        });
        chatStore.save();
        scrollToBottom();

        const host = getAgentHost();
        const token = getVigyanToken();
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (token) headers["X-Vigyan-Token"] = token;

        try {
          const res = await fetch(`${host}/api/ingest/file`, {
            method: "POST",
            headers,
            body: JSON.stringify({
              filename: file.name,
              content: content.slice(0, 10000),
            }),
          });
          if (res.ok) {
            const data = await res.json();
            chatStore.messages.push({
              id: uid(),
              role: "assistant",
              content: data.summary,
              thinking: "Parsed text parameters directly on local machine.\n",
              thinkingDone: true,
              streaming: false,
              digest: {
                filename: file.name,
                summary: data.summary,
                metrics: data.metrics || [],
                actions: data.suggested_actions || ["Synthesize 3D CAD Enclosure"],
              },
            });
            chatStore.save();
            scrollToBottom();
          }
        } catch (err) {
          send(`I have imported '${file.name}'. Analyze parameters:\n\n\`\`\`\n${content.slice(0, 2000)}\n\`\`\``);
        }
      };
      reader.readAsText(file);
    }
  }

  function handleActionClick(actionText: string) {
    if (actionText.includes("3D") || actionText.includes("Enclosure") || actionText.includes("CAD")) {
      send("Generate a 3D CAD enclosure based on extracted specifications.");
    } else if (actionText.includes("KiCad") || actionText.includes("PCB") || actionText.includes("Netlist")) {
      send("Generate KiCad PCB netlist based on extracted specifications.");
    } else {
      send(actionText);
    }
  }

  const fontClass: Record<"sm" | "md" | "lg", string> = {
    sm: "text-[13px]",
    md: "text-[15px]",
    lg: "text-[16px]",
  };

  function uid() {
    return Math.random().toString(36).slice(2, 10);
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
    });
  }

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;

    input = "";
    if (textareaEl) {
      textareaEl.style.height = "auto";
    }
    isStreaming = true;

    // Add user message to persistent reactive store
    chatStore.messages.push({
      id: uid(),
      role: "user",
      content: trimmed,
      thinking: "",
      thinkingDone: false,
      streaming: false,
    });
    chatStore.save();

    // Add placeholder assistant message
    const assistantId = uid();
    chatStore.messages.push({
      id: assistantId,
      role: "assistant",
      content: "",
      thinking: "",
      thinkingDone: false,
      streaming: true,
      toolResults: [],
    });

    scrollToBottom();

    // Build conversation history
    const history = chatStore.messages
      .filter((m) => m.role === "user" || (m.role === "assistant" && m.content))
      .slice(0, -1)
      .map((m) => ({ role: m.role, content: m.content }));

    abortController = new AbortController();

    await streamChat(
      [...history, { role: "user", content: trimmed }],
      model || DEFAULT_MODEL,
      (chunk) => {
        const idx = chatStore.messages.findIndex((m) => m.id === assistantId);
        if (idx === -1) return;

        if (chunk.type === "thinking") {
          chatStore.messages[idx].thinking += chunk.text;
          scrollToBottom();
        } else if (chunk.type === "sympy") {
          chatStore.messages[idx].sympyGrounding = chunk.text;
          if (!chatStore.messages[idx].thinking.includes("SymPy")) {
            chatStore.messages[idx].thinking = `[SymPy AST Verified]: ${chunk.text}\n` + chatStore.messages[idx].thinking;
          }
          scrollToBottom();
        } else if (chunk.type === "tool_result") {
          if (!chatStore.messages[idx].toolResults) {
            chatStore.messages[idx].toolResults = [];
          }
          if (chunk.toolData) {
            chatStore.messages[idx].toolResults.push(chunk.toolData);
          }
          scrollToBottom();
        } else if (chunk.type === "answer") {
          if (!chatStore.messages[idx].thinkingDone) chatStore.messages[idx].thinkingDone = true;
          chatStore.messages[idx].content += chunk.text;
          scrollToBottom();
        } else if (chunk.type === "done" || chunk.type === "error") {
          chatStore.messages[idx].thinkingDone = true;
          chatStore.messages[idx].streaming = false;
          if (chunk.type === "error") {
            chatStore.messages[idx].content = chunk.text;
          }
          chatStore.save();
          isStreaming = false;
        }
      },
      abortController.signal,
    );

    isStreaming = false;
    chatStore.save();
    scrollToBottom();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  function stop() {
    abortController?.abort();
    isStreaming = false;
    const last = chatStore.messages.at(-1);
    if (last && last.role === "assistant") {
      last.streaming = false;
      last.thinkingDone = true;
      if (!last.content) last.content = "Generation halted.";
      chatStore.save();
    }
  }
</script>

<div class="flex flex-col h-full bg-[#000000] text-[#f3f4f6] {fontClass[fontSize]}">

  <!-- Centered Message Canvas (768px reading container) -->
  <div
    bind:this={scrollEl}
    class="flex-1 overflow-y-auto overscroll-contain px-4 py-6 scroll-smooth"
    style="scrollbar-width: none;"
  >
    <div class="max-w-[768px] mx-auto w-full flex flex-col gap-4">

      {#if chatStore.messages.length === 0}
        <!-- Welcome Hero -->
        <div class="flex flex-col items-center justify-center min-h-[52vh] text-center gap-6 animate-fade-in select-none">
          <div class="flex flex-col items-center gap-3">
            <div class="w-12 h-12 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center shadow-lg">
              <svg class="w-7 h-7 text-[#ffffff]" viewBox="0 0 100 100" fill="currentColor">
                <polygon points="50,90 20,20 38,20 50,65 62,20 80,20" />
              </svg>
            </div>
            <h1 class="text-2xl font-bold text-white tracking-tight">Vigyan Pro</h1>
            <p class="text-[#9ca3af] text-[14px] max-w-md leading-relaxed">
              Sovereign STEM intelligence. Exact mathematical grounding via SymPy AST, circuit simulation, and 100% offline inference.
            </p>
          </div>

          <!-- Starter Chips -->
          <div class="flex flex-wrap justify-center gap-2.5 mt-1">
            {#each STARTERS as s}
              <button
                onclick={() => send(s.prompt)}
                class="flex items-center gap-2 px-3.5 py-2 rounded-full bg-[#08090d] border border-white/10 text-xs text-[#9ca3af] hover:text-white hover:border-white/25 transition-all shadow-sm"
              >
                <span class="text-sm font-mono text-[#10b981]">{s.icon}</span>
                <span>{s.label}</span>
              </button>
            {/each}
          </div>
        </div>
      {:else}
        <!-- Message Thread -->
        {#each chatStore.messages as msg (msg.id)}
          {#if msg.role === "user"}
            <MessageBubble
              role="user"
              content={msg.content}
              attachment={msg.attachment}
            />
          {:else}
            <div class="flex flex-col gap-2">
              {#if msg.thinking || (msg.streaming && !msg.thinkingDone)}
                <ThinkingBlock
                  text={msg.thinking}
                  streaming={msg.streaming && !msg.thinkingDone}
                  done={msg.thinkingDone}
                  sympyGrounding={msg.sympyGrounding}
                />
              {/if}
              {#if msg.content || (msg.toolResults && msg.toolResults.length > 0) || (msg.thinkingDone && msg.streaming) || msg.digest}
                <MessageBubble
                  role="assistant"
                  content={msg.content}
                  streaming={msg.streaming}
                  toolResults={msg.toolResults}
                  sympyGrounding={msg.sympyGrounding}
                  digest={msg.digest}
                  onAction={handleActionClick}
                />
              {/if}
            </div>
          {/if}
        {/each}
      {/if}

    </div>
  </div>

  <!-- Floating Bottom Input Dock (macOS Pebble Island style) with Drag & Drop Ingestion -->
  <div
    class="px-4 pb-4 pt-1 flex-shrink-0 z-20 relative"
    ondragover={(e) => { e.preventDefault(); isDragging = true; }}
    ondragleave={() => (isDragging = false)}
    ondrop={handleFileDrop}
    role="region"
    aria-label="Chat input and file drop dock"
  >
    <!-- Hidden file input for attachment button -->
    <input
      type="file"
      bind:this={fileInputEl}
      onchange={handleFileInputChange}
      accept="image/*,.pdf,.csv,.txt,.json,.py,.kicad_pcb,.stl,.md"
      class="hidden"
    />

    <div class="max-w-[720px] mx-auto w-full flex flex-col items-center">
      {#if isDragging}
        <div class="w-full mb-2 py-3 px-4 rounded-2xl bg-[#10b981]/15 border-2 border-dashed border-[#10b981] flex items-center justify-center gap-2 text-xs text-[#10b981] font-semibold animate-pulse">
          <span>⇪</span>
          <span>Drop PDF, CSV, or Datasheet to Analyze with Sovereign AI</span>
        </div>
      {/if}

      <div class="w-full flex items-center gap-3 bg-[rgba(12,14,20,0.92)] backdrop-blur-xl border border-white/10 rounded-full px-4 py-2.5 shadow-[0_8px_32px_rgba(0,0,0,0.7)] focus-within:border-white/25 transition-all">
        <!-- Attachment button for local document ingestion -->
        <button
          type="button"
          onclick={() => fileInputEl?.click()}
          class="w-7 h-7 rounded-full text-[#9ca3af] hover:text-white hover:bg-white/[0.08] flex items-center justify-center transition-all flex-shrink-0"
          title="Import Datasheet, PDF, or CSV"
        >
          <svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M15.621 4.379a3 3 0 00-4.242 0l-7 7a3 3 0 004.241 4.243h.001l.497-.5a.75.75 0 011.064 1.057l-.498.501-.002.002a4.5 4.5 0 01-6.364-6.364l7-7a4.5 4.5 0 016.368 6.36l-3.455 3.553A2.625 2.625 0 119.5 9.525l3.45-3.451a.75.75 0 111.061 1.06l-3.45 3.451a1.125 1.125 0 001.587 1.595l3.454-3.553a3 3 0 00.02-4.248z" clip-rule="evenodd" />
          </svg>
        </button>

        <textarea
          bind:this={textareaEl}
          bind:value={input}
          oninput={autoResize}
          onkeydown={handleKeydown}
          placeholder="Ask a STEM question, generate a 3D enclosure, or drop a datasheet…"
          rows={1}
          disabled={isStreaming}
          class="flex-1 bg-transparent text-[#ffffff] placeholder-[#6b7280] outline-none resize-none leading-relaxed disabled:opacity-50 max-h-36 overflow-y-auto text-[14px]"
          style="scrollbar-width: none;"
        ></textarea>

        {#if isStreaming}
          <button
            onclick={stop}
            class="flex-shrink-0 w-8 h-8 rounded-full bg-white/10 border border-white/20 text-[#e2e8f0] hover:bg-white/20 flex items-center justify-center transition-all"
            title="Stop generation"
          >
            <span class="w-2.5 h-2.5 bg-white rounded-sm block"></span>
          </button>
        {:else}
          <button
            onclick={() => send(input)}
            disabled={!input.trim()}
            class="flex-shrink-0 w-8 h-8 rounded-full bg-white text-black flex items-center justify-center disabled:opacity-30 hover:opacity-90 transition-all shadow-md font-bold cursor-pointer"
            title="Send (Enter)"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 translate-y-[-0.5px]">
              <path fill-rule="evenodd" d="M10 17a.75.75 0 01-.75-.75V5.612L5.29 9.77a.75.75 0 01-1.08-1.04l5.25-5.5a.75.75 0 011.08 0l5.25 5.5a.75.75 0 11-1.08 1.04l-3.96-4.158V16.25A.75.75 0 0110 17z" clip-rule="evenodd"/>
            </svg>
          </button>
        {/if}
      </div>

      <p class="text-[10px] text-[#6b7280] text-center mt-2 tracking-wide select-none">
        100% Air-Gapped · Sovereign Compute · SymPy AST & Parametric CSG
      </p>
    </div>
  </div>

</div>

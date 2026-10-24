<script lang="ts">
  import { renderMath, extractPlottableFormula } from "../lib/katex";
  import PlotModal from "./PlotModal.svelte";
  import StemInlineCard from "./StemInlineCard.svelte";
  import AttachmentCard from "./AttachmentCard.svelte";
  import SecurityGateCard from "./SecurityGateCard.svelte";
  import type { ToolResult } from "../lib/ollama";
  import type { Attachment, Digest } from "../lib/chatStore.svelte";

  interface Props {
    role: "user" | "assistant";
    content: string;
    streaming?: boolean;
    toolResults?: ToolResult[];
    sympyGrounding?: string;
    attachment?: Attachment;
    digest?: Digest;
    onAction?: (actionText: string) => void;
  }
  let { role, content, streaming = false, toolResults = [], sympyGrounding, attachment, digest, onAction }: Props = $props();

  const isUser = $derived(role === "user");

  // Render math in assistant messages
  const rendered = $derived(
    isUser ? content : renderMath(content)
  );

  // Check if a mathematical formula can be plotted (if not already handled by toolResults)
  const plottableFormula = $derived(
    !isUser && !streaming && toolResults.length === 0 ? extractPlottableFormula(content) : null
  );

  let plotModalOpen = $state(false);
</script>

<div class="flex w-full animate-fade-in {isUser ? 'justify-end' : 'justify-start'} my-1">
  <div
    class="
      max-w-[85%] leading-relaxed break-words
      {isUser
        ? 'bg-[#181a24] border border-[rgba(255,255,255,0.12)] text-[#f3f4f6] px-5 py-3 rounded-2xl rounded-tr-sm font-medium shadow-md'
        : 'bg-[#08090d] border border-[rgba(255,255,255,0.08)] text-[#e2e8f0] px-5 py-4 rounded-2xl rounded-tl-sm shadow-md w-full'}
    "
  >
    {#if isUser}
      {#if attachment}
        <AttachmentCard {attachment} />
      {/if}
      {#if content}
        <p class="whitespace-pre-wrap text-[14px]">{content}</p>
      {/if}
    {:else}
      {#if digest}
        <div class="mb-3 p-3.5 rounded-xl bg-[#0c0e14] border border-white/10 space-y-3">
          <div class="flex items-center justify-between text-xs">
            <span class="font-semibold text-white flex items-center gap-1.5">
              <span class="text-[#10b981]">📋</span>
              <span>Engineering Digest: {digest.filename}</span>
            </span>
            <span class="text-[10px] text-[#10b981] bg-[#10b981]/10 px-2 py-0.5 rounded border border-[#10b981]/20 font-mono">
              OCR Processed
            </span>
          </div>

          <p class="text-xs text-[#9ca3af] leading-relaxed">
            {digest.summary}
          </p>

          {#if digest.metrics && digest.metrics.length > 0}
            <div class="flex flex-wrap gap-1.5 pt-1">
              {#each digest.metrics as m}
                <span class="text-[11px] font-mono bg-white/[0.05] border border-white/10 text-white px-2 py-0.5 rounded">
                  {m}
                </span>
              {/each}
            </div>
          {/if}

          {#if digest.actions && digest.actions.length > 0}
            <div class="pt-2 border-t border-white/[0.06] flex flex-wrap gap-2">
              {#each digest.actions as act}
                <button
                  type="button"
                  onclick={() => onAction?.(act)}
                  class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white text-black hover:bg-slate-200 text-xs font-semibold shadow transition-all cursor-pointer"
                >
                  <span>⚡</span>
                  <span>{act}</span>
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
      <!-- Inline STEM visualizer cards (2D curves, 3D meshes, circuits) -->
      {#if toolResults && toolResults.length > 0}
        <div class="mb-3 space-y-2">
          {#each toolResults as t}
            {#if t.status === "requires_approval" || (t.command && t.risk)}
              <SecurityGateCard
                command={t.command}
                risk={t.risk || "medium"}
                reason={t.reason}
                cwd={t.cwd}
              />
            {:else}
              <StemInlineCard tool={t} />
            {/if}
          {/each}
        </div>
      {/if}

      <!-- Assistant text response with offline KaTeX typography -->
      <!-- eslint-disable-next-line svelte/no-at-html-tags -->
      <div class="prose-vigyan text-[14px]">{@html rendered}{#if streaming}<span class="animate-blink text-[#10b981] ml-0.5">▋</span>{/if}</div>

      <!-- 1-Click Interactive Plot Curve Button (for extracted formulas) -->
      {#if plottableFormula}
        <button
          onclick={() => (plotModalOpen = true)}
          class="mt-3.5 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#10b981]/10 border border-[#10b981]/30 text-[#10b981] hover:bg-[#10b981]/20 text-xs font-medium transition-all"
        >
          <span>📈</span>
          <span>Plot Curve ({plottableFormula})</span>
        </button>
      {/if}
    {/if}
  </div>
</div>

{#if plottableFormula}
  <PlotModal
    formula={plottableFormula}
    isOpen={plotModalOpen}
    onClose={() => (plotModalOpen = false)}
  />
{/if}

<style>
  :global(.prose-vigyan .katex) {
    font-size: 1.08em;
  }
  :global(.prose-vigyan .katex-display) {
    margin: 0.8em 0;
    overflow-x: auto;
    padding: 0.4em 0;
  }
  :global(.prose-vigyan .inline-code) {
    font-family: "SF Mono", "Cascadia Code", "Fira Code", monospace;
    font-size: 0.88em;
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    padding: 0.15em 0.4em;
    color: #e2e8f0;
  }
</style>

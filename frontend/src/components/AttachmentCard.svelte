<script lang="ts">
  // AttachmentCard.svelte — Quiet Luxury Obsidian File & Image Preview Pill
  // Replaces raw binary dumps with a sleek 56px thumbnail and expandable view.
  import type { Attachment } from "../lib/chatStore.svelte";

  interface Props {
    attachment: Attachment;
  }
  let { attachment }: Props = $props();

  let previewModalOpen = $state(false);

  function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
</script>

<div class="mb-2 flex items-center gap-3 p-2.5 rounded-xl bg-[#0a0c12] border border-white/10 shadow-sm max-w-md animate-fade-in">
  {#if attachment.type === "image" && attachment.dataUrl}
    <!-- 56px Rounded Image Thumbnail -->
    <button
      type="button"
      onclick={() => (previewModalOpen = true)}
      class="w-14 h-14 rounded-lg overflow-hidden border border-white/10 flex-shrink-0 relative group cursor-pointer focus:outline-none"
      title="Click to expand full resolution"
    >
      <img
        src={attachment.dataUrl}
        alt={attachment.name}
        class="w-full h-full object-cover group-hover:scale-105 transition-transform"
      />
      <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-xs">
        ⛶
      </div>
    </button>
  {:else}
    <!-- Document Icon -->
    <div class="w-14 h-14 rounded-lg bg-white/[0.04] border border-white/10 flex flex-col items-center justify-center flex-shrink-0 text-[#10b981]">
      <span class="text-xl">📄</span>
    </div>
  {/if}

  <div class="flex-1 min-w-0 pr-2">
    <div class="flex items-center gap-2">
      <span class="text-xs font-semibold text-white truncate max-w-[200px]">
        {attachment.name}
      </span>
      <span class="text-[10px] font-mono text-[#10b981] bg-[#10b981]/10 px-1.5 py-0.5 rounded border border-[#10b981]/20">
        {attachment.type === "image" ? "Image" : "Document"}
      </span>
    </div>
    <div class="text-[11px] text-[#9ca3af] mt-0.5">
      {formatBytes(attachment.size)} · Ingested for Sovereign STEM Analysis
    </div>
  </div>
</div>

<!-- Full-Resolution Preview Modal -->
{#if previewModalOpen && attachment.dataUrl}
  <button
    type="button"
    class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md cursor-default border-0"
    onclick={() => (previewModalOpen = false)}
    aria-label="Close Preview"
  ></button>

  <div class="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 max-w-[90vw] max-h-[85vh] bg-[#0c0e14] border border-white/15 rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-fade-in">
    <div class="flex items-center justify-between px-4 py-2.5 border-b border-white/10 bg-[#10121a]">
      <span class="text-xs font-semibold text-white">{attachment.name}</span>
      <button
        onclick={() => (previewModalOpen = false)}
        class="text-gray-400 hover:text-white p-1 text-sm leading-none"
      >
        ✕
      </button>
    </div>
    <div class="p-4 bg-black flex items-center justify-center overflow-auto max-h-[75vh]">
      <img src={attachment.dataUrl} alt={attachment.name} class="max-h-full max-w-full rounded object-contain" />
    </div>
  </div>
{/if}

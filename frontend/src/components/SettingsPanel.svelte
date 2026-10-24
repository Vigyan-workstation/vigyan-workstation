<script lang="ts">
  // SettingsPanel — Quiet Luxury Slide-in Drawer
  // Steve Jobs Principle: Simple, un-cluttered, zero developer plumbing.
  import { getAvailableModels, DEFAULT_MODEL } from "../lib/ollama";
  import { chatStore } from "../lib/chatStore.svelte";

  interface Props {
    open: boolean;
    model: string;
    fontSize: "sm" | "md" | "lg";
    onClose: () => void;
    onModelChange: (m: string) => void;
    onFontSizeChange: (s: "sm" | "md" | "lg") => void;
  }

  let {
    open,
    model,
    fontSize,
    onClose,
    onModelChange,
    onFontSizeChange,
  }: Props = $props();

  let availableModels = $state<string[]>([DEFAULT_MODEL]);
  let loading = $state(false);
  let confirmReset = $state(false);
  let resetTimer: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    if (open) {
      loading = true;
      getAvailableModels().then((list) => {
        if (list.length > 0) availableModels = list;
        loading = false;
      });
    }
  });

  const fontLabels: Record<"sm" | "md" | "lg", string> = {
    sm: "Compact",
    md: "Standard",
    lg: "Large",
  };

  function handleResetChat() {
    if (!confirmReset) {
      confirmReset = true;
      if (resetTimer) clearTimeout(resetTimer);
      resetTimer = setTimeout(() => { confirmReset = false; }, 3500);
    } else {
      confirmReset = false;
      if (resetTimer) clearTimeout(resetTimer);
      chatStore.clear();
      onClose();
    }
  }
</script>

<!-- Backdrop Blur -->
{#if open}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm border-0 cursor-default"
    onclick={onClose}
    aria-label="Close settings"
  ></button>
{/if}

<!-- Slide-in Drawer -->
<aside
  class="fixed top-0 right-0 h-full w-80 z-50 flex flex-col bg-[#08090d] border-l border-[rgba(255,255,255,0.08)] shadow-2xl transition-transform duration-300 {open
    ? 'translate-x-0'
    : 'translate-x-full'}"
  style="will-change: transform;"
>
  <!-- Header -->
  <div class="flex items-center justify-between px-6 py-4 border-b border-[rgba(255,255,255,0.06)] bg-[#0c0e14]">
    <span class="text-xs font-semibold text-white tracking-wider uppercase">Preferences</span>
    <button
      onclick={onClose}
      class="text-[#9ca3af] hover:text-white transition-colors text-base leading-none p-1"
      aria-label="Close"
    >✕</button>
  </div>

  <!-- Content -->
  <div class="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-6">

    <!-- Model Selection -->
    <section>
      <label for="ai-engine-select" class="text-[11px] font-semibold uppercase tracking-wider text-[#9ca3af] block mb-2">AI Engine</label>
      {#if loading}
        <div class="text-xs text-[#9ca3af] italic py-2">Discovering local models…</div>
      {:else}
        <div class="relative">
          <select
            id="ai-engine-select"
            value={model}
            onchange={(e) => onModelChange((e.target as HTMLSelectElement).value)}
            class="w-full bg-[#10121a] border border-[rgba(255,255,255,0.1)] text-white text-xs rounded-xl px-3.5 py-2.5 outline-none focus:border-white/30 transition-colors appearance-none cursor-pointer"
          >
            {#each availableModels as m}
              <option value={m} class="bg-[#08090d] text-white">
                {m === "vigyan:1.5b" ? "Vigyan 1.5B Quad-Master (Recommended)" : m}
              </option>
            {/each}
          </select>
          <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-[#9ca3af]">
            <svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd"/>
            </svg>
          </div>
        </div>
        <p class="text-[11px] text-[#6b7280] mt-1.5 leading-relaxed">
          100% sovereign compute. No external servers or API calls.
        </p>
      {/if}
    </section>

    <!-- Reading Size -->
    <section>
      <span class="text-[11px] font-semibold uppercase tracking-wider text-[#9ca3af] block mb-2">Typography Size</span>
      <div class="flex gap-2 bg-[#10121a] p-1 rounded-xl border border-[rgba(255,255,255,0.08)]">
        {#each (["sm", "md", "lg"] as ("sm" | "md" | "lg")[]) as size}
          <button
            onclick={() => onFontSizeChange(size)}
            class="flex-1 py-1.5 rounded-lg text-xs transition-all {fontSize === size
              ? 'bg-white text-black font-semibold shadow-sm'
              : 'text-[#9ca3af] hover:text-white'}"
          >
            {fontLabels[size]}
          </button>
        {/each}
      </div>
    </section>

    <!-- Conversation & Privacy -->
    <section>
      <span class="text-[11px] font-semibold uppercase tracking-wider text-[#9ca3af] block mb-2">Privacy & Storage</span>
      <div class="bg-[#10121a] border border-[rgba(255,255,255,0.08)] rounded-xl p-3.5 space-y-3">
        <p class="text-[11px] text-[#9ca3af] leading-relaxed">
          All conversation history and mathematical traces reside strictly on your local disk.
        </p>
        <button
          onclick={handleResetChat}
          class="w-full py-2 px-3 rounded-lg text-xs font-medium transition-all border {confirmReset
            ? 'bg-rose-950/60 border-rose-500 text-rose-200 animate-pulse'
            : 'bg-white/[0.03] border-white/10 text-rose-400 hover:bg-rose-950/20 hover:border-rose-800/40'}"
        >
          {confirmReset ? "Confirm: Reset Conversation?" : "Clear Chat History"}
        </button>
      </div>
    </section>

  </div>
</aside>

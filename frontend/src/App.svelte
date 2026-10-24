<script lang="ts">
  // App.svelte — Root Obsidian Executive Frame
  // Minimalist, quiet luxury desktop interface inspired by Steve Jobs Apple typography.
  import { onMount } from "svelte";
  import Chat from "./components/Chat.svelte";
  import SettingsPanel from "./components/SettingsPanel.svelte";
  import StatusDot from "./components/StatusDot.svelte";
  import StudioCanvas from "./components/StudioCanvas.svelte";
  import { checkOllamaStatus, DEFAULT_MODEL } from "./lib/ollama";
  import { chatStore } from "./lib/chatStore.svelte";
  import { studioStore } from "./lib/studioStore.svelte";

  let settingsOpen = $state(false);
  let ollamaConnected = $state(false);
  let model = $state(DEFAULT_MODEL);
  let fontSize = $state<"sm" | "md" | "lg">("md");

  onMount(() => {
    const check = async () => {
      ollamaConnected = await checkOllamaStatus();
    };
    check();
    const interval = setInterval(check, 8_000);
    return () => clearInterval(interval);
  });
</script>

<div class="h-screen w-screen flex flex-col bg-[#000000] text-[#f3f4f6] select-none overflow-hidden font-sans">

  <!-- Header: 44px, translucent obsidian titanium glassmorphic bar -->
  <header class="h-11 flex-shrink-0 px-5 flex items-center justify-between border-b border-[rgba(255,255,255,0.08)] bg-[rgba(8,9,13,0.88)] backdrop-blur-md z-30">

    <!-- Left: Minimalist Vector Metallic V Monogram + Name -->
    <div class="flex items-center gap-2.5">
      <div class="w-6 h-6 rounded-lg bg-white/[0.06] border border-white/10 flex items-center justify-center shadow-sm">
        <svg class="w-3.5 h-3.5 text-white" viewBox="0 0 100 100" fill="currentColor">
          <polygon points="50,90 20,20 38,20 50,65 62,20 80,20" />
        </svg>
      </div>
      <span class="text-[13px] font-semibold tracking-wider text-white">Vigyan Pro</span>
    </div>

    <!-- Center: Sovereign Status Pill with Glowing Green Micro-Dot -->
    <StatusDot connected={ollamaConnected} />

    <!-- Right: Executive Actions (+ New Chat, Studio Canvas & Settings Gear) -->
    <div class="flex items-center gap-2">
      {#if studioStore.activeArtifact && !studioStore.isOpen}
        <button
          onclick={() => (studioStore.isOpen = true)}
          class="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium text-[#10b981] bg-[#10b981]/10 border border-[#10b981]/30 hover:bg-[#10b981]/20 transition-all shadow-sm"
          title="Re-open STEM Studio Canvas"
        >
          <span>⬡</span>
          <span>Studio Canvas</span>
        </button>
      {/if}

      {#if chatStore.messages.length > 0}
        <button
          onclick={() => chatStore.clear()}
          class="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium text-[#9ca3af] hover:text-white bg-white/[0.03] hover:bg-white/[0.08] border border-white/10 hover:border-white/20 transition-all shadow-sm"
          title="Start fresh conversation"
        >
          <span class="text-xs leading-none">+</span>
          <span>New Chat</span>
        </button>
      {/if}

      <!-- Settings gear -->
      <button
        onclick={() => (settingsOpen = !settingsOpen)}
        class="w-8 h-8 flex items-center justify-center rounded-full text-[#9ca3af] hover:text-white hover:bg-white/[0.08] transition-all"
        aria-label="Settings"
        title="Settings"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
          <path
            fill-rule="evenodd"
            d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
            clip-rule="evenodd"
          />
        </svg>
      </button>
    </div>
  </header>

  <!-- Main: Responsive Split Workspace (Centered Chat + Side-by-Side Studio Canvas) -->
  <main class="flex-1 overflow-hidden relative flex">
    <div class="h-full transition-all duration-300 {studioStore.isOpen ? 'w-[52%] border-r border-[rgba(255,255,255,0.08)]' : 'w-full'}">
      <Chat {model} {fontSize} />
    </div>

    {#if studioStore.isOpen}
      <div class="h-full w-[48%] flex-shrink-0 animate-fade-in">
        <StudioCanvas />
      </div>
    {/if}
  </main>

  <!-- Settings Slide-in Drawer -->
  <SettingsPanel
    open={settingsOpen}
    {model}
    {fontSize}
    onClose={() => (settingsOpen = false)}
    onModelChange={(m) => (model = m)}
    onFontSizeChange={(s) => (fontSize = s)}
  />

</div>

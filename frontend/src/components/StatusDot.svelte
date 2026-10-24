<script lang="ts">
  // StatusDot — Shows air-gapped sovereign status in center header
  // Matches Steve Jobs concept: 100% Offline · 1.5B Quad-Master with subtle green dot
  interface Props {
    connected: boolean;
  }
  let { connected }: Props = $props();
</script>

<div class="flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.08] select-none shadow-sm">
  <!-- Glowing Micro-Dot -->
  <span
    class="w-1.5 h-1.5 rounded-full flex-shrink-0 transition-colors duration-700 {connected
      ? 'bg-[#10b981] animate-pulse-dot shadow-[0_0_8px_rgba(16,185,129,0.8)]'
      : 'bg-[#52525b]'}"
  ></span>
  <!-- Label -->
  <span class="text-[11px] font-medium text-[#9ca3af] tracking-wide">
    {connected ? "100% Offline · 1.5B Quad-Master" : "Connecting AI…"}
  </span>
</div>

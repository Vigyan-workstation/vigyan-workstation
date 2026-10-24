<script lang="ts">
  // SecurityGateCard.svelte — Luxury Human-in-the-Loop Terminal Authorization Gate
  // Steve Jobs Obsidian Titanium design system for system commands.
  import { getAgentHost, getVigyanToken } from "../lib/ollama";

  interface Props {
    command: string;
    risk?: "low" | "medium" | "high";
    reason?: string;
    cwd?: string;
    onExecuted?: (output: string, success: boolean) => void;
  }
  let { command, risk = "medium", reason = "System modification requested", cwd, onExecuted }: Props = $props();

  let isExecuting = $state(false);
  let isDone = $state(false);
  let outputText = $state("");
  let isSuccess = $state(true);
  let isDismissed = $state(false);

  async function authorizeAndRun() {
    isExecuting = true;
    try {
      const host = getAgentHost();
      const token = getVigyanToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["X-Vigyan-Token"] = token;

      const res = await fetch(`${host}/api/agent/execute_cmd`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          command,
          confirmed: true,
          cwd,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        isSuccess = !!data.success;
        outputText = data.stdout || data.output || data.stderr || (data.success ? "Command executed cleanly." : "Command completed with errors.");
      } else {
        isSuccess = false;
        outputText = `HTTP ${res.status}: Command execution failed.`;
      }
    } catch (e: any) {
      isSuccess = false;
      outputText = `Execution error: ${e.message}`;
    } finally {
      isExecuting = false;
      isDone = true;
      onExecuted?.(outputText, isSuccess);
    }
  }
</script>

{#if !isDismissed}
  <div class="my-3 w-full rounded-xl border border-[rgba(255,255,255,0.08)] bg-[#08090d] overflow-hidden shadow-xl animate-fade-in">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-2.5 border-b border-[rgba(255,255,255,0.06)] bg-[#0c0e14]">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full {isDone ? (isSuccess ? 'bg-[#10b981]' : 'bg-[#ef4444]') : (risk === 'high' ? 'bg-[#ef4444]' : 'bg-[#f59e0b]')} shadow-[0_0_6px_currentColor]"></span>
        <span class="text-xs font-semibold text-white tracking-wide">
          {isDone ? "Terminal Command Executed" : "System Action Authorization"}
        </span>
      </div>

      <span class="text-[10px] font-mono px-2 py-0.5 rounded border {risk === 'high' ? 'text-[#ef4444] bg-[#ef4444]/10 border-[#ef4444]/30' : 'text-[#f59e0b] bg-[#f59e0b]/10 border-[#f59e0b]/30'} uppercase">
        {risk} Risk
      </span>
    </div>

    <!-- Body -->
    <div class="p-4 space-y-3">
      <div>
        <p class="text-xs text-[#9ca3af] mb-1.5 leading-relaxed">{reason}</p>
        <div class="bg-black/90 p-3 rounded-lg border border-white/[0.08] font-mono text-xs text-[#e2e8f0] flex items-center justify-between">
          <span class="text-[#38bdf8] select-all">$ {command}</span>
          {#if cwd}
            <span class="text-[10px] text-[#6b7280]">{cwd}</span>
          {/if}
        </div>
      </div>

      {#if isDone}
        <!-- Terminal Output -->
        <div class="bg-black p-3 rounded-lg border border-white/[0.08] font-mono text-[11px] max-h-48 overflow-y-auto space-y-1">
          <div class="text-[10px] text-[#6b7280] flex justify-between border-b border-white/[0.05] pb-1">
            <span>Terminal Output:</span>
            <span class={isSuccess ? "text-[#10b981]" : "text-[#ef4444]"}>{isSuccess ? "Exit 0 (Success)" : "Error"}</span>
          </div>
          <pre class="text-[#d1d5db] whitespace-pre-wrap">{outputText}</pre>
        </div>
      {:else}
        <!-- Action Buttons -->
        <div class="pt-1 flex items-center gap-2">
          <button
            type="button"
            disabled={isExecuting}
            onclick={authorizeAndRun}
            class="flex-1 py-2.5 px-4 rounded-xl bg-white text-black hover:bg-slate-200 text-xs font-semibold tracking-wide flex items-center justify-center gap-2 transition-all shadow-md cursor-pointer disabled:opacity-50"
          >
            {#if isExecuting}
              <span class="w-3 h-3 rounded-full border-2 border-black border-t-transparent animate-spin"></span>
              <span>Executing…</span>
            {:else}
              <span>⚡</span>
              <span>Authorize & Run Command</span>
            {/if}
          </button>

          <button
            type="button"
            disabled={isExecuting}
            onclick={() => (isDismissed = true)}
            class="py-2.5 px-4 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-[#9ca3af] hover:text-white border border-white/[0.06] text-xs font-medium transition-all cursor-pointer"
          >
            Cancel
          </button>
        </div>
      {/if}
    </div>
  </div>
{/if}

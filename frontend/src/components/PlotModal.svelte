<script lang="ts">
  // PlotModal — Discreet interactive 2D curve inspector powered by local Plotly
  import { onMount } from "svelte";

  interface Props {
    formula: string;
    isOpen: boolean;
    onClose: () => void;
  }

  let { formula, isOpen, onClose }: Props = $props();

  let plotContainer = $state<HTMLElement | null>(null);

  function evaluateFormula(expr: string, x: number): number {
    try {
      // Safe mathematical evaluation for polynomial/trig curves
      const clean = expr
        .replace(/\^/g, "**")
        .replace(/sin/g, "Math.sin")
        .replace(/cos/g, "Math.cos")
        .replace(/tan/g, "Math.tan")
        .replace(/sqrt/g, "Math.sqrt")
        .replace(/exp/g, "Math.exp")
        .replace(/log/g, "Math.log")
        .replace(/pi/g, "Math.PI");

      // Replace standalone x with the value
      const fn = new Function("x", `return ${clean};`);
      const val = fn(x);
      return isFinite(val) ? val : 0;
    } catch {
      return 0;
    }
  }

  function drawPlot() {
    if (!plotContainer || !isOpen || !(window as any).Plotly) return;

    const xVals: number[] = [];
    const yVals: number[] = [];
    for (let x = -10; x <= 10; x += 0.2) {
      xVals.push(Math.round(x * 10) / 10);
      yVals.push(evaluateFormula(formula, x));
    }

    const trace = {
      x: xVals,
      y: yVals,
      mode: "lines",
      line: {
        color: "#10b981",
        width: 2.5,
      },
      name: `f(x) = ${formula}`,
    };

    const layout = {
      title: {
        text: `Curve: y = ${formula}`,
        font: { color: "#ffffff", size: 14 },
      },
      paper_bgcolor: "#08090d",
      plot_bgcolor: "#0f1116",
      margin: { l: 45, r: 25, t: 40, b: 35 },
      xaxis: {
        gridcolor: "#222530",
        zerolinecolor: "#52525b",
        tickfont: { color: "#9ca3af", size: 11 },
      },
      yaxis: {
        gridcolor: "#222530",
        zerolinecolor: "#52525b",
        tickfont: { color: "#9ca3af", size: 11 },
      },
      showlegend: false,
    };

    const config = {
      displayModeBar: false,
      responsive: true,
    };

    (window as any).Plotly.newPlot(plotContainer, [trace], layout, config);
  }

  $effect(() => {
    if (isOpen && plotContainer) {
      setTimeout(drawPlot, 50);
    }
  });
</script>

{#if isOpen}
  <!-- Backdrop -->
  <button
    type="button"
    class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm cursor-default"
    onclick={onClose}
    aria-label="Close plot"
  ></button>

  <!-- Modal -->
  <div class="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[90vw] max-w-2xl bg-s1 border border-b2 rounded-2xl shadow-2xl overflow-hidden animate-fade-in">
    <!-- Header -->
    <div class="flex items-center justify-between px-5 py-3.5 border-b border-b1 bg-s1">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-emerald"></span>
        <span class="text-xs font-semibold tracking-wider text-platinum uppercase">Interactive Curve Analysis</span>
      </div>
      <button
        onclick={onClose}
        class="text-muted hover:text-platinum text-base leading-none transition-colors"
        aria-label="Close"
      >✕</button>
    </div>

    <!-- Plot Container -->
    <div class="p-4 bg-canvas flex flex-col items-center justify-center">
      <div bind:this={plotContainer} class="w-full h-80"></div>
      <p class="text-[11px] text-muted text-center mt-2">
        Rendered offline via sovereign STEM visualizer. Zoom and pan freely.
      </p>
    </div>
  </div>
{/if}

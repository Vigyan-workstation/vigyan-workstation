<script lang="ts">
  // StemInlineCard — Sovereign Inline STEM Visualizer Card
  // Obsidian Satin Titanium design system. Renders 2D curves, 3D manifolds, waveforms, robotics, and STEM calculations inline.
  import { onMount } from "svelte";
  import type { ToolResult } from "../lib/ollama";
  import { studioStore, type StudioArtifact } from "../lib/studioStore.svelte";

  interface Props {
    tool: ToolResult;
  }
  let { tool }: Props = $props();

  let plotContainer = $state<HTMLElement | null>(null);
  let waveContainer = $state<HTMLElement | null>(null);
  let modalOpen = $state(false);

  const isPlot = $derived(
    tool.tool === "plot" ||
    tool.tool === "evaluate_plot" ||
    (tool.data && Array.isArray(tool.data)) ||
    (tool.x && tool.y)
  );

  const isCAD = $derived(
    tool.render_type === "threejs_cad" ||
    tool.tool === "cad_model_generate" ||
    !!tool.mesh
  );

  const isPCB = $derived(
    tool.render_type === "pcb_netlist" ||
    tool.tool === "pcb_netlist_generate" ||
    !!tool.kicad_netlist
  );

  const isRobotics = $derived(
    tool.render_type === "robotics" ||
    tool.tool === "robotics_kinematics" ||
    !!tool.joint_chain
  );

  const isWave = $derived(
    tool.render_type === "wavedrom" ||
    tool.tool === "wavedrom_generate" ||
    !!tool.wavedrom_spec
  );

  const isSilicon = $derived(
    tool.render_type === "silicon_eda" ||
    tool.tool === "verilog_analyze"
  );

  const isMaterial = $derived(
    tool.render_type === "material_science" ||
    tool.tool === "material_science"
  );

  const isBiology = $derived(
    tool.render_type === "biology_viewer" ||
    tool.tool === "biology_viewer"
  );

  const isMedical = $derived(
    tool.render_type === "medical_viewer" ||
    tool.tool === "medical_viewer"
  );

  const isMath3D = $derived(
    tool.render_type === "math_visualizer" ||
    tool.tool === "math_visualizer"
  );

  function openInStudio() {
    const artifact: StudioArtifact = {
      id: Math.random().toString(36).slice(2, 9),
      tool: tool.tool,
      render_type: tool.render_type || (isCAD ? "threejs_cad" : isPCB ? "pcb_netlist" : isRobotics ? "robotics" : isWave ? "wavedrom" : "stem"),
      title: tool.title || (isCAD ? "Parametric 3D CAD" : isPCB ? "KiCad Netlist" : isRobotics ? "6-DoF Robotics Kinematics" : isWave ? "Digital Bus Timing" : "STEM Visualizer"),
      shape: tool.shape,
      parameters: tool.parameters,
      mesh: tool.mesh,
      stl_base64: tool.stl_base64,
      dimensions_mm: tool.dimensions_mm,
      triangle_count: tool.triangle_count,
      circuit_type: tool.circuit_type,
      kicad_netlist: tool.kicad_netlist,
      components: tool.components,
      nets: tool.nets,
      arm_type: tool.arm_type,
      joint_angles_deg: tool.joint_angles_deg,
      end_effector: tool.end_effector,
      reach_mm: tool.reach_mm,
      joint_chain: tool.joint_chain,
      metrics: tool.metrics,
      wavedrom_spec: tool.wavedrom_spec,
      protocol: tool.protocol,
      module_name: tool.module_name,
      clock_domains: tool.clock_domains,
      ports: tool.ports,
    };
    studioStore.open(artifact);
  }

  // Automatically reveal studio canvas on CAD, PCB, Robotics, or WaveDrom generation
  onMount(() => {
    if (isCAD || isPCB || isRobotics || isWave) {
      setTimeout(openInStudio, 80);
    }
    if (isWave && waveContainer) {
      setTimeout(renderInlineWave, 60);
    }
  });

  function renderInlineWave() {
    if (!waveContainer || typeof (window as any).WaveDrom === "undefined") return;
    try {
      const spec = tool.wavedrom_spec;
      if (!spec) return;
      waveContainer.innerHTML = "";
      const uidPrefix = "wd_inline_" + Math.random().toString(36).slice(2, 7) + "_";
      const targetDiv = document.createElement("div");
      targetDiv.id = uidPrefix + "0";
      waveContainer.appendChild(targetDiv);
      (window as any).WaveDrom.RenderWaveForm(0, spec, uidPrefix);
    } catch (e) {
      console.warn("WaveDrom inline render error:", e);
    }
  }

  function renderPlot(targetEl: HTMLElement, height = 240) {
    if (!targetEl || !(window as any).Plotly) return;

    let traces: any[] = [];
    if (tool.data && Array.isArray(tool.data)) {
      traces = tool.data;
    } else if (tool.x && tool.y) {
      traces = [
        {
          x: tool.x,
          y: tool.y,
          mode: "lines",
          line: { color: "#10b981", width: 2 },
          name: tool.title || "Curve",
        },
      ];
    }

    const layout = {
      title: false,
      paper_bgcolor: "#08090d",
      plot_bgcolor: "#000000",
      height,
      margin: { l: 45, r: 20, t: 20, b: 35 },
      xaxis: {
        gridcolor: "#161820",
        zerolinecolor: "#272a38",
        tickfont: { color: "#9ca3af", size: 10 },
      },
      yaxis: {
        gridcolor: "#161820",
        zerolinecolor: "#272a38",
        tickfont: { color: "#9ca3af", size: 10 },
      },
      showlegend: false,
    };

    const config = {
      displayModeBar: false,
      responsive: true,
    };

    try {
      (window as any).Plotly.newPlot(targetEl, traces, layout, config);
    } catch {}
  }

  $effect(() => {
    if (isPlot && plotContainer) {
      setTimeout(() => renderPlot(plotContainer!), 50);
    }
    if (isWave && waveContainer) {
      setTimeout(() => renderInlineWave(), 50);
    }
  });

  let modalContainer = $state<HTMLElement | null>(null);
  $effect(() => {
    if (modalOpen && modalContainer && isPlot) {
      setTimeout(() => renderPlot(modalContainer!, 420), 80);
    }
  });
</script>

<div class="my-3 w-full rounded-xl border border-[rgba(255,255,255,0.08)] bg-[#08090d] overflow-hidden shadow-lg transition-all">
  <!-- Card Header -->
  <div class="flex items-center justify-between px-4 py-2.5 border-b border-[rgba(255,255,255,0.06)] bg-[#0c0e14]">
    <div class="flex items-center gap-2">
      <span class="w-2 h-2 rounded-full bg-[#10b981] shadow-[0_0_6px_rgba(16,185,129,0.7)]"></span>
      <span class="text-xs font-semibold tracking-wide text-[#e2e8f0]">
        {tool.title || (isPlot ? "2D Curve Analysis" : isCAD ? "3D Parametric CAD" : isPCB ? "KiCad Electronic Netlist" : isRobotics ? "6-DoF Robotics Kinematics" : isWave ? "Digital Bus Timing Diagram" : isSilicon ? "Silicon RTL Static Analysis" : isMaterial ? "Materials Crystallography" : isBiology ? "Molecular Biology" : isMedical ? "Clinical Protocol" : "STEM Visualizer")}
      </span>
      {#if tool.expression}
        <span class="text-[11px] font-mono text-[#9ca3af] bg-white/[0.04] px-2 py-0.5 rounded border border-white/[0.05]">
          {tool.expression}
        </span>
      {/if}
    </div>

    {#if isPlot}
      <button
        onclick={() => (modalOpen = true)}
        class="text-[11px] text-[#9ca3af] hover:text-white flex items-center gap-1 px-2 py-1 rounded bg-white/[0.03] hover:bg-white/[0.08] transition-colors"
        title="Expand full view"
      >
        <span>⛶</span>
        <span>Inspect</span>
      </button>
    {:else if isCAD || isPCB || isRobotics || isWave}
      <button
        onclick={openInStudio}
        class="text-[11px] text-[#10b981] hover:text-white flex items-center gap-1 px-2.5 py-1 rounded bg-[#10b981]/10 hover:bg-[#10b981]/20 border border-[#10b981]/30 transition-all font-medium cursor-pointer"
      >
        <span>⬡</span>
        <span>Studio View</span>
      </button>
    {/if}
  </div>

  <!-- Card Body -->
  {#if isPlot}
    <div class="p-2 bg-black">
      <div bind:this={plotContainer} class="w-full h-[240px]"></div>
    </div>

  <!-- 3D CAD MODEL -->
  {:else if isCAD}
    <div class="p-4 flex flex-col gap-3 bg-[#08090d]">
      <div class="flex items-center justify-between text-xs text-[#9ca3af]">
        <span>Shape: <strong class="text-white uppercase">{tool.shape || "Enclosure"}</strong></span>
        {#if tool.triangle_count}
          <span class="font-mono text-[#10b981]">{tool.triangle_count} Triangles · 100% Manifold</span>
        {/if}
      </div>

      {#if tool.parameters}
        <div class="grid grid-cols-3 gap-2 bg-[#0c0e14] p-3 rounded-xl border border-white/[0.05] text-xs">
          {#each Object.entries(tool.parameters) as [k, v]}
            <div class="flex flex-col">
              <span class="text-[10px] text-[#6b7280] uppercase">{k}</span>
              <span class="font-mono text-white font-semibold">{v}{typeof v === 'number' && k !== 'num_teeth' ? 'mm' : ''}</span>
            </div>
          {/each}
        </div>
      {/if}

      <button
        onclick={openInStudio}
        class="w-full py-2.5 px-4 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] border border-white/10 hover:border-white/20 text-white font-medium text-xs flex items-center justify-center gap-2 transition-all shadow-sm cursor-pointer"
      >
        <span class="text-[#10b981]">⬡</span>
        <span>Open in 3D Studio Canvas ➔</span>
      </button>
    </div>

  <!-- KICAD PCB NETLIST -->
  {:else if isPCB}
    <div class="p-4 flex flex-col gap-3 bg-[#08090d]">
      <div class="flex items-center justify-between text-xs text-[#9ca3af]">
        <span>Topology: <strong class="text-white">{tool.circuit_type || "555 Astable"}</strong></span>
        {#if tool.components}
          <span class="font-mono text-[#10b981]">{tool.components.length} Components</span>
        {/if}
      </div>

      <button
        onclick={openInStudio}
        class="w-full py-2.5 px-4 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] border border-white/10 hover:border-white/20 text-white font-medium text-xs flex items-center justify-center gap-2 transition-all shadow-sm cursor-pointer"
      >
        <span class="text-[#10b981]">⚡</span>
        <span>Open in KiCad Netlist Studio ➔</span>
      </button>
    </div>

  <!-- 6-DOF ROBOTICS KINEMATICS -->
  {:else if isRobotics}
    <div class="p-4 flex flex-col gap-3 bg-[#08090d]">
      <div class="flex items-center justify-between text-xs text-[#9ca3af]">
        <span>Manipulator: <strong class="text-white">{tool.arm_type || "6-DoF Industrial Arm"}</strong></span>
        {#if tool.reach_mm}
          <span class="font-mono text-[#10b981]">Reach: {tool.reach_mm} mm</span>
        {/if}
      </div>

      {#if tool.end_effector}
        <div class="grid grid-cols-3 gap-2 bg-[#0c0e14] p-3 rounded-xl border border-white/[0.05] text-xs font-mono">
          <div class="flex flex-col">
            <span class="text-[10px] text-[#6b7280]">END-EFFECTOR X</span>
            <span class="text-white font-semibold">{tool.end_effector.x?.toFixed(1) ?? 0} mm</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] text-[#6b7280]">END-EFFECTOR Y</span>
            <span class="text-white font-semibold">{tool.end_effector.y?.toFixed(1) ?? 0} mm</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] text-[#6b7280]">END-EFFECTOR Z</span>
            <span class="text-[#10b981] font-semibold">{tool.end_effector.z?.toFixed(1) ?? 0} mm</span>
          </div>
        </div>
      {/if}

      <button
        onclick={openInStudio}
        class="w-full py-2.5 px-4 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] border border-white/10 hover:border-white/20 text-white font-medium text-xs flex items-center justify-center gap-2 transition-all shadow-sm cursor-pointer"
      >
        <span class="text-[#10b981]">🦾</span>
        <span>Open in Robotics Kinematics Studio ➔</span>
      </button>
    </div>

  <!-- WAVEDROM DIGITAL TIMING -->
  {:else if isWave}
    <div class="p-4 flex flex-col gap-3 bg-[#08090d]">
      <div class="flex items-center justify-between text-xs text-[#9ca3af]">
        <span>Digital Protocol: <strong class="text-white uppercase font-mono">{tool.protocol || "SPI Master"}</strong></span>
        <span class="text-[10px] text-[#10b981] bg-[#10b981]/10 px-2 py-0.5 rounded border border-[#10b981]/20">WaveDrom</span>
      </div>

      <div class="bg-[#040508] p-3 rounded-xl border border-white/[0.06] overflow-x-auto min-h-[140px] flex items-center justify-center">
        <div bind:this={waveContainer} class="w-full overflow-x-auto"></div>
      </div>

      <button
        onclick={openInStudio}
        class="w-full py-2.5 px-4 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] border border-white/10 hover:border-white/20 text-white font-medium text-xs flex items-center justify-center gap-2 transition-all shadow-sm cursor-pointer"
      >
        <span class="text-[#10b981]">⏱</span>
        <span>Open in Waveform Studio ➔</span>
      </button>
    </div>

  <!-- SILICON EDA / VERILOG -->
  {:else if isSilicon}
    <div class="p-4 flex flex-col gap-3 bg-[#08090d]">
      <div class="flex items-center justify-between text-xs text-[#9ca3af]">
        <span>Module: <strong class="text-white font-mono">{tool.module_name || "rtl_top"}</strong></span>
        <span class="text-[10px] text-[#38bdf8] bg-[#38bdf8]/10 px-2 py-0.5 rounded border border-[#38bdf8]/20">{tool.engine || "Sovereign RTL"}</span>
      </div>

      {#if tool.metrics}
        <div class="grid grid-cols-3 gap-2 bg-[#0c0e14] p-3 rounded-xl border border-white/[0.05] text-xs">
          {#each tool.metrics as m}
            <div class="flex flex-col">
              <span class="text-[10px] text-[#6b7280]">{m.label}</span>
              <span class="font-mono text-white font-semibold">{m.value}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>

  <!-- MATERIALS SCIENCE -->
  {:else if isMaterial}
    <div class="p-4 flex flex-col gap-3 bg-[#08090d]">
      <div class="flex items-center justify-between text-xs text-[#9ca3af]">
        <span>Lattice: <strong class="text-white">{tool.latticeType || "FCC"}</strong></span>
        <span class="text-[#10b981] font-mono">Bragg Diffraction Ready</span>
      </div>
      <div class="grid grid-cols-3 gap-2 bg-[#0c0e14] p-3 rounded-xl border border-white/[0.05] text-xs">
        <div class="flex flex-col">
          <span class="text-[10px] text-[#6b7280]">ATOMIC PACKING</span>
          <span class="font-mono text-white font-semibold">{tool.latticeType === 'BCC' ? '0.68' : '0.74'}</span>
        </div>
        <div class="flex flex-col">
          <span class="text-[10px] text-[#6b7280]">COORDINATION NO.</span>
          <span class="font-mono text-white font-semibold">{tool.latticeType === 'BCC' ? '8' : '12'}</span>
        </div>
        <div class="flex flex-col">
          <span class="text-[10px] text-[#6b7280]">MILLER PLANES</span>
          <span class="font-mono text-[#10b981] font-semibold">(111), (100)</span>
        </div>
      </div>
    </div>

  <!-- MOLECULAR BIOLOGY -->
  {:else if isBiology}
    <div class="p-4 flex flex-col gap-3 bg-[#08090d]">
      <div class="flex items-center justify-between text-xs text-[#9ca3af]">
        <span>System: <strong class="text-white">{tool.type?.replace('_', ' ').toUpperCase() || "B-DNA HELIX"}</strong></span>
        <span class="text-[#38bdf8] font-mono text-[11px]">10.5 bp / Turn</span>
      </div>
      <div class="bg-[#0c0e14] p-3 rounded-xl border border-white/[0.05] text-xs flex justify-between items-center font-mono">
        <span class="text-[#38bdf8]">■ A - ■ T (2 H-Bonds)</span>
        <span class="text-[#10b981]">■ G ≡ ■ C (3 H-Bonds)</span>
      </div>
    </div>

  <!-- CLINICAL MEDICAL -->
  {:else if isMedical}
    <div class="p-4 flex flex-col gap-3 bg-[#08090d]">
      <div class="flex items-center justify-between text-xs text-[#9ca3af]">
        <span>Protocol: <strong class="text-white">{tool.condition?.toUpperCase() || "STEMI PROTOCOL"}</strong></span>
        <span class="text-[#ef4444] font-semibold text-[11px] bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">Critical Care</span>
      </div>
      <div class="bg-[#0c0e14] p-3 rounded-xl border border-white/[0.05] text-xs font-mono space-y-1">
        <div class="text-[#9ca3af]">Diagnostic Criteria: ST elevation in &ge; 2 contiguous leads</div>
        <div class="text-[#10b981]">Action: Immediate catheterization lab activation &lt; 90 min door-to-balloon</div>
      </div>
    </div>

  <!-- CIRCUIT SIMULATION -->
  {:else if tool.tool === "circuit" || tool.filter_type}
    <div class="p-4 text-xs font-mono text-[#e2e8f0] space-y-1.5 bg-[#08090d]">
      <div class="text-[#10b981] font-semibold">Circuit Simulation Parameters:</div>
      {#each Object.entries(tool.parameters || {}) as [k, v]}
        <div class="flex justify-between border-b border-white/[0.04] py-1">
          <span class="text-[#9ca3af]">{k}:</span>
          <span class="text-white font-bold">{v}</span>
        </div>
      {/each}
      {#if tool.cutoff_hz}
        <div class="flex justify-between pt-1 text-[#10b981]">
          <span>Cutoff Frequency (fc):</span>
          <span>{tool.cutoff_hz.toFixed(2)} Hz</span>
        </div>
      {/if}
    </div>

  <!-- GENERAL STEM CARD -->
  {:else}
    <div class="p-4 text-xs font-mono text-[#e2e8f0] space-y-1 bg-[#08090d]">
      {#each Object.entries(tool) as [k, v]}
        {#if k !== "tool" && k !== "render_type" && typeof v !== "object"}
          <div class="flex justify-between border-b border-white/[0.04] py-1">
            <span class="text-[#9ca3af]">{k}:</span>
            <span class="text-white">{String(v)}</span>
          </div>
        {/if}
      {/each}
    </div>
  {/if}
</div>

<!-- Modal Full View for 2D Plots -->
{#if modalOpen}
  <button
    type="button"
    class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md cursor-default"
    onclick={() => (modalOpen = false)}
    aria-label="Close"
  ></button>

  <div class="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[92vw] max-w-3xl bg-[#08090d] border border-[rgba(255,255,255,0.12)] rounded-2xl shadow-2xl overflow-hidden animate-fade-in">
    <div class="flex items-center justify-between px-5 py-3 border-b border-[rgba(255,255,255,0.08)] bg-[#0c0e14]">
      <div class="flex items-center gap-2">
        <span class="w-2.5 h-2.5 rounded-full bg-[#10b981]"></span>
        <span class="text-xs font-semibold tracking-wider text-white uppercase">
          {tool.title || "Interactive STEM Inspector"}
        </span>
      </div>
      <button
        onclick={() => (modalOpen = false)}
        class="text-gray-400 hover:text-white text-base leading-none transition-colors cursor-pointer"
      >✕</button>
    </div>

    <div class="p-5 bg-black flex flex-col items-center">
      <div bind:this={modalContainer} class="w-full h-[420px]"></div>
      <p class="text-[11px] text-[#9ca3af] mt-3">
        Rendered 100% offline via Sovereign STEM Visualizer Engine.
      </p>
    </div>
  </div>
{/if}

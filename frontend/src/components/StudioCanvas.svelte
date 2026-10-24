<script lang="ts">
  // StudioCanvas.svelte — Side-by-Side Multi-Mode STEM Engineering Workstation
  // Steve Jobs Obsidian Titanium monochrome viewport with tactile real-time controls.
  // Supports: 3D CAD, KiCad Netlists, 6-DoF Robotics Kinematics, and WaveDrom Digital Waveforms.
  import { onMount, onDestroy } from "svelte";
  import { studioStore } from "../lib/studioStore.svelte";
  import { getAgentHost, getVigyanToken } from "../lib/ollama";

  let canvasEl = $state<HTMLCanvasElement | null>(null);
  let threeScene: any = null;
  let threeCamera: any = null;
  let threeRenderer: any = null;
  let threeControls: any = null;
  let threeMesh: any = null;
  let animationFrameId: number | null = null;
  let autoRotate = $state(true);
  let isRecomputing = $state(false);

  // Local copy of CAD sliders
  let currentParams = $state<Record<string, number>>({});
  let recomputeTimer: ReturnType<typeof setTimeout> | null = null;

  // Local copy of Robotics joint angles
  let jointAngles = $state<number[]>([0, 0, 0, 0, 0, 0]);
  let roboticsTimer: ReturnType<typeof setTimeout> | null = null;

  // WaveDrom container element
  let waveContainerEl = $state<HTMLDivElement | null>(null);

  $effect(() => {
    const art = studioStore.activeArtifact;
    if (art && art.parameters) {
      currentParams = { ...art.parameters };
    }
    if (art && art.joint_angles_deg && Array.isArray(art.joint_angles_deg)) {
      jointAngles = [...art.joint_angles_deg];
    }
  });

  onMount(() => {
    initThreeViewport();
    window.addEventListener("resize", onWindowResize);
    return () => {
      window.removeEventListener("resize", onWindowResize);
      cleanupThree();
    };
  });

  onDestroy(() => {
    cleanupThree();
  });

  function initThreeViewport() {
    if (!canvasEl || typeof (window as any).THREE === "undefined") return;

    const THREE = (window as any).THREE;
    const width = canvasEl.clientWidth || 400;
    const height = canvasEl.clientHeight || 340;

    threeScene = new THREE.Scene();
    threeScene.background = new THREE.Color(0x040508);

    threeCamera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    threeCamera.position.set(160, 140, 180);

    threeRenderer = new THREE.WebGLRenderer({
      canvas: canvasEl,
      antialias: true,
      alpha: true,
    });
    threeRenderer.setSize(width, height);
    threeRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Studio Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
    threeScene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.9);
    dirLight1.position.set(100, 150, 100);
    threeScene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x38bdf8, 0.35);
    dirLight2.position.set(-100, -80, -100);
    threeScene.add(dirLight2);

    // Orbit Controls
    if ((window as any).OrbitControls) {
      threeControls = new (window as any).OrbitControls(threeCamera, canvasEl);
      threeControls.enableDamping = true;
      threeControls.dampingFactor = 0.08;
      threeControls.target.set(0, 0, 0);
    }

    buildMesh();
    animate();
  }

  function buildMesh() {
    if (!threeScene || typeof (window as any).THREE === "undefined") return;
    const THREE = (window as any).THREE;
    const art = studioStore.activeArtifact;
    if (!art || !art.mesh || !art.mesh.positions) return;

    if (threeMesh) {
      threeScene.remove(threeMesh);
      threeMesh.geometry.dispose();
      threeMesh.material.dispose();
      threeMesh = null;
    }

    const pos = new Float32Array(art.mesh.positions);
    const norm = new Float32Array(art.mesh.normals);

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geometry.setAttribute("normal", new THREE.BufferAttribute(norm, 3));

    // Quiet luxury metallic satin titanium material
    const material = new THREE.MeshStandardMaterial({
      color: 0xd1d5db,
      metalness: 0.6,
      roughness: 0.35,
      wireframe: false,
    });

    threeMesh = new THREE.Mesh(geometry, material);
    threeScene.add(threeMesh);

    // Compute bounding sphere to frame camera
    geometry.computeBoundingSphere();
    if (geometry.boundingSphere && threeControls) {
      const radius = geometry.boundingSphere.radius || 60;
      threeCamera.position.set(radius * 2.2, radius * 1.8, radius * 2.2);
      threeControls.target.copy(geometry.boundingSphere.center);
      threeControls.update();
    }
  }

  function animate() {
    animationFrameId = requestAnimationFrame(animate);
    if (autoRotate && threeMesh) {
      threeMesh.rotation.y += 0.006;
    }
    if (threeControls) {
      threeControls.update();
    }
    if (threeRenderer && threeScene && threeCamera) {
      threeRenderer.render(threeScene, threeCamera);
    }
  }

  function onWindowResize() {
    if (!canvasEl || !threeRenderer || !threeCamera) return;
    const width = canvasEl.clientWidth;
    const height = canvasEl.clientHeight;
    threeCamera.aspect = width / height;
    threeCamera.updateProjectionMatrix();
    threeRenderer.setSize(width, height);
  }

  function cleanupThree() {
    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId);
      animationFrameId = null;
    }
    if (threeRenderer) {
      threeRenderer.dispose();
      threeRenderer = null;
    }
    threeScene = null;
    threeCamera = null;
    threeControls = null;
    threeMesh = null;
  }

  $effect(() => {
    if (studioStore.activeArtifact?.mesh && threeScene) {
      buildMesh();
    }
  });

  // Re-render WaveDrom diagram whenever activeArtifact changes
  $effect(() => {
    const art = studioStore.activeArtifact;
    if (art?.render_type === "wavedrom" && art.wavedrom_spec && waveContainerEl) {
      setTimeout(() => renderWaveDrom(), 40);
    }
  });

  function renderWaveDrom() {
    if (!waveContainerEl || typeof (window as any).WaveDrom === "undefined") return;
    try {
      const art = studioStore.activeArtifact;
      if (!art || !art.wavedrom_spec) return;
      waveContainerEl.innerHTML = "";
      const uidPrefix = "wd_studio_" + Math.random().toString(36).slice(2, 7) + "_";
      const targetDiv = document.createElement("div");
      targetDiv.id = uidPrefix + "0";
      waveContainerEl.appendChild(targetDiv);
      (window as any).WaveDrom.RenderWaveForm(0, art.wavedrom_spec, uidPrefix);
    } catch (e) {
      console.warn("WaveDrom Studio render error:", e);
    }
  }

  // CAD Param changes
  function handleParamChange(key: string, value: number) {
    currentParams[key] = value;
    if (recomputeTimer) clearTimeout(recomputeTimer);
    recomputeTimer = setTimeout(async () => {
      isRecomputing = true;
      try {
        const art = studioStore.activeArtifact;
        if (!art) return;
        const host = getAgentHost();
        const token = getVigyanToken();
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (token) headers["X-Vigyan-Token"] = token;

        const res = await fetch(`${host}/api/tools/cad/recompute`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            shape: art.shape || "enclosure",
            params: currentParams,
            title: art.title,
          }),
        });

        if (res.ok) {
          const data = await res.json();
          if (data.success && data.mesh) {
            studioStore.updateParameters(currentParams, data.mesh, data.stl_base64);
          }
        }
      } catch (e) {
        console.error("CAD recompute error:", e);
      } finally {
        isRecomputing = false;
      }
    }, 120);
  }

  // Robotics joint angle slider adjustments
  function handleJointChange(index: number, deg: number) {
    jointAngles[index] = deg;
    if (roboticsTimer) clearTimeout(roboticsTimer);
    roboticsTimer = setTimeout(async () => {
      isRecomputing = true;
      try {
        const host = getAgentHost();
        const token = getVigyanToken();
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (token) headers["X-Vigyan-Token"] = token;

        const res = await fetch(`${host}/api/tools/robotics/recompute`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            arm_type: studioStore.activeArtifact?.arm_type || "6dof_industrial",
            joint_angles_deg: jointAngles,
          }),
        });

        if (res.ok) {
          const data = await res.json();
          if (data.success) {
            studioStore.updateRobotics(
              jointAngles,
              data.end_effector,
              data.reach_mm,
              data.joint_chain,
              data.metrics
            );
          }
        }
      } catch (e) {
        console.error("Robotics recompute error:", e);
      } finally {
        isRecomputing = false;
      }
    }, 100);
  }

  // Robotics Pose Presets
  const ROBOTICS_PRESETS = [
    { label: "Home (0°)", angles: [0, 0, 0, 0, 0, 0] },
    { label: "Pick & Place", angles: [30, 45, -60, 0, 15, 0] },
    { label: "Full Reach", angles: [0, 90, -10, 0, 0, 0] },
    { label: "High Lift", angles: [0, 15, -15, 0, 90, 0] },
  ];

  function applyRoboticsPreset(angles: number[]) {
    jointAngles = [...angles];
    handleJointChange(0, angles[0]);
  }

  // WaveDrom Protocol Presets
  const WAVEDROM_PRESETS = [
    { id: "spi_master", label: "SPI Master" },
    { id: "i2c_bus", label: "I2C 7-Bit" },
    { id: "uart_frame", label: "UART 8N1" },
    { id: "axi4_stream", label: "AXI4-Stream" },
  ];

  async function applyWaveDromPreset(proto: string) {
    isRecomputing = true;
    try {
      const host = getAgentHost();
      const token = getVigyanToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["X-Vigyan-Token"] = token;

      const res = await fetch(`${host}/api/tools/wavedrom/recompute`, {
        method: "POST",
        headers,
        body: JSON.stringify({ protocol: proto }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.success && data.wavedrom_spec) {
          studioStore.updateWave(data.wavedrom_spec, proto);
          setTimeout(renderWaveDrom, 50);
        }
      }
    } catch (e) {
      console.error("WaveDrom recompute error:", e);
    } finally {
      isRecomputing = false;
    }
  }

  // Exporters
  function downloadSTL() {
    const art = studioStore.activeArtifact;
    if (!art || !art.stl_base64) return;
    const binStr = atob(art.stl_base64);
    const bytes = new Uint8Array(binStr.length);
    for (let i = 0; i < binStr.length; i++) bytes[i] = binStr.charCodeAt(i);
    const blob = new Blob([bytes], { type: "model/stl" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(art.shape || "vigyan_cad").toLowerCase()}_3d_model.stl`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function downloadNetlist() {
    const art = studioStore.activeArtifact;
    if (!art || !art.kicad_netlist) return;
    const blob = new Blob([art.kicad_netlist], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(art.circuit_type || "vigyan_circuit").toLowerCase()}.net`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function downloadWaveSVG() {
    if (!waveContainerEl) return;
    const svgEl = waveContainerEl.querySelector("svg");
    if (!svgEl) return;
    const svgData = new XMLSerializer().serializeToString(svgEl);
    const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "digital_timing_waveform.svg";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function downloadRoboticsJSON() {
    const art = studioStore.activeArtifact;
    if (!art) return;
    const data = {
      arm_type: art.arm_type,
      joint_angles_deg: art.joint_angles_deg,
      end_effector: art.end_effector,
      reach_mm: art.reach_mm,
      joint_chain: art.joint_chain,
      metrics: art.metrics,
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "robotics_kinematics.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
</script>

<aside
  class="h-full w-full flex flex-col bg-[#07080c] border-l border-[rgba(255,255,255,0.08)] shadow-2xl overflow-hidden animate-fade-in"
>
  <!-- Studio Header -->
  <div class="h-11 flex-shrink-0 px-4 flex items-center justify-between border-b border-[rgba(255,255,255,0.06)] bg-[#0b0d13]">
    <div class="flex items-center gap-2">
      <div class="w-5 h-5 rounded bg-white/[0.08] flex items-center justify-center text-[10px] font-mono text-[#10b981]">
        ⬡
      </div>
      <span class="text-xs font-semibold text-white tracking-wide truncate max-w-[220px]">
        {studioStore.activeArtifact?.title || "STEM Studio Canvas"}
      </span>
      <span class="text-[10px] font-mono text-[#10b981] bg-[#10b981]/10 px-2 py-0.5 rounded border border-[#10b981]/20">
        Live Studio
      </span>
    </div>

    <div class="flex items-center gap-2">
      {#if studioStore.activeArtifact?.mesh}
        <button
          onclick={() => (autoRotate = !autoRotate)}
          class="text-[11px] px-2 py-0.5 rounded border transition-all {autoRotate
            ? 'bg-white/10 text-white border-white/20'
            : 'text-[#9ca3af] border-transparent hover:text-white'}"
          title="Toggle 360 Turntable Orbit"
        >
          ↻ Orbit
        </button>
      {/if}

      <button
        onclick={() => studioStore.close()}
        class="text-[#9ca3af] hover:text-white transition-colors p-1 text-sm leading-none"
        aria-label="Close Studio Canvas"
      >
        ✕
      </button>
    </div>
  </div>

  <!-- Main Canvas Viewport -->
  <div class="flex-1 overflow-y-auto flex flex-col">
    <!-- MODE 1: 3D CAD MODEL -->
    {#if studioStore.activeArtifact?.render_type === "threejs_cad" || studioStore.activeArtifact?.mesh}
      <div class="relative w-full h-[360px] bg-[#040508] border-b border-white/[0.06] flex-shrink-0">
        <canvas bind:this={canvasEl} class="w-full h-full cursor-grab active:cursor-grabbing"></canvas>
        {#if isRecomputing}
          <div class="absolute top-3 left-3 flex items-center gap-2 px-2.5 py-1 rounded-full bg-black/70 backdrop-blur border border-white/10 text-[11px] text-[#10b981]">
            <span class="w-2 h-2 rounded-full bg-[#10b981] animate-ping"></span>
            <span>Recomputing CSG Math…</span>
          </div>
        {/if}
        <div class="absolute bottom-2.5 right-3 text-[10px] text-[#6b7280] select-none">
          Click & Drag to Rotate · Scroll to Zoom
        </div>
      </div>

      <!-- Tactile Sliders -->
      <div class="p-5 flex-1 flex flex-col gap-4">
        <div>
          <h3 class="text-xs font-semibold uppercase tracking-wider text-[#9ca3af] mb-1">
            Tactile Physical Dimensions
          </h3>
          <p class="text-[11px] text-[#6b7280]">
            Adjust dimensions with sliders. Exact geometry recomputes in real time.
          </p>
        </div>

        {#if studioStore.activeArtifact?.shape === "enclosure" || studioStore.activeArtifact?.shape === "box"}
          <div class="space-y-3 bg-[#0c0e14] p-3.5 rounded-xl border border-white/[0.06]">
            <div>
              <div class="flex justify-between text-xs text-[#e2e8f0] mb-1">
                <span>Width (X)</span>
                <span class="font-mono text-[#10b981] font-semibold">{currentParams.width ?? 120} mm</span>
              </div>
              <input
                type="range"
                min="50"
                max="260"
                step="2"
                value={currentParams.width ?? 120}
                oninput={(e) => handleParamChange("width", parseFloat((e.target as HTMLInputElement).value))}
                class="w-full accent-[#10b981] bg-white/10 h-1.5 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            <div>
              <div class="flex justify-between text-xs text-[#e2e8f0] mb-1">
                <span>Length (Y)</span>
                <span class="font-mono text-[#10b981] font-semibold">{currentParams.length ?? 80} mm</span>
              </div>
              <input
                type="range"
                min="40"
                max="200"
                step="2"
                value={currentParams.length ?? 80}
                oninput={(e) => handleParamChange("length", parseFloat((e.target as HTMLInputElement).value))}
                class="w-full accent-[#10b981] bg-white/10 h-1.5 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            <div>
              <div class="flex justify-between text-xs text-[#e2e8f0] mb-1">
                <span>Height (Z)</span>
                <span class="font-mono text-[#10b981] font-semibold">{currentParams.height ?? 35} mm</span>
              </div>
              <input
                type="range"
                min="15"
                max="100"
                step="1"
                value={currentParams.height ?? 35}
                oninput={(e) => handleParamChange("height", parseFloat((e.target as HTMLInputElement).value))}
                class="w-full accent-[#10b981] bg-white/10 h-1.5 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            {#if studioStore.activeArtifact?.shape === "enclosure"}
              <div>
                <div class="flex justify-between text-xs text-[#e2e8f0] mb-1">
                  <span>Wall Thickness</span>
                  <span class="font-mono text-[#10b981] font-semibold">{currentParams.wall ?? 2.5} mm</span>
                </div>
                <input
                  type="range"
                  min="1.5"
                  max="5.0"
                  step="0.5"
                  value={currentParams.wall ?? 2.5}
                  oninput={(e) => handleParamChange("wall", parseFloat((e.target as HTMLInputElement).value))}
                  class="w-full accent-[#10b981] bg-white/10 h-1.5 rounded-lg appearance-none cursor-pointer"
                />
              </div>
            {/if}
          </div>
        {:else if studioStore.activeArtifact?.shape === "gear"}
          <div class="space-y-3 bg-[#0c0e14] p-3.5 rounded-xl border border-white/[0.06]">
            <div>
              <div class="flex justify-between text-xs text-[#e2e8f0] mb-1">
                <span>Teeth Count</span>
                <span class="font-mono text-[#10b981] font-semibold">{currentParams.num_teeth ?? 18}</span>
              </div>
              <input
                type="range"
                min="8"
                max="40"
                step="1"
                value={currentParams.num_teeth ?? 18}
                oninput={(e) => handleParamChange("num_teeth", parseInt((e.target as HTMLInputElement).value))}
                class="w-full accent-[#10b981] bg-white/10 h-1.5 rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        {/if}

        <div class="mt-auto pt-2">
          <button
            onclick={downloadSTL}
            class="w-full py-3 px-4 rounded-xl bg-white text-black font-semibold text-xs tracking-wide flex items-center justify-center gap-2 hover:bg-slate-200 transition-all shadow-lg cursor-pointer"
          >
            <span>⬇ Download 3D Print File (.STL)</span>
          </button>
        </div>
      </div>

    <!-- MODE 2: ROBOTICS KINEMATICS -->
    {:else if studioStore.activeArtifact?.render_type === "robotics" || studioStore.activeArtifact?.tool === "robotics_kinematics"}
      <div class="p-5 flex-1 flex flex-col gap-4">
        <!-- Pose Viewport (2D/3D Kinematic Skeleton Projection) -->
        <div class="relative w-full h-[220px] bg-[#040508] rounded-xl border border-white/[0.08] overflow-hidden flex items-center justify-center">
          <svg class="w-full h-full" viewBox="-500 -500 1000 600">
            <!-- Grid Lines & Reach Circle -->
            <circle cx="0" cy="0" r="400" fill="none" stroke="#161822" stroke-width="2" stroke-dasharray="4,4" />
            <line x1="-480" y1="0" x2="480" y2="0" stroke="#161822" stroke-width="1.5" />
            <line x1="0" y1="-480" x2="0" y2="100" stroke="#161822" stroke-width="1.5" />

            <!-- Joint Skeleton Chain -->
            {#if studioStore.activeArtifact.joint_chain && studioStore.activeArtifact.joint_chain.length > 1}
              <!-- Link lines -->
              {#each studioStore.activeArtifact.joint_chain as pt, idx}
                {#if idx < studioStore.activeArtifact.joint_chain.length - 1}
                  {@const next = studioStore.activeArtifact.joint_chain[idx + 1]}
                  <line
                    x1={pt.x * 0.45}
                    y1={-pt.z * 0.45}
                    x2={next.x * 0.45}
                    y2={-next.z * 0.45}
                    stroke="#10b981"
                    stroke-width="5"
                    stroke-linecap="round"
                  />
                {/if}
              {/each}

              <!-- Joint nodes -->
              {#each studioStore.activeArtifact.joint_chain as pt, idx}
                <circle
                  cx={pt.x * 0.45}
                  cy={-pt.z * 0.45}
                  r={idx === 0 ? 8 : idx === studioStore.activeArtifact.joint_chain.length - 1 ? 7 : 5}
                  fill={idx === studioStore.activeArtifact.joint_chain.length - 1 ? "#38bdf8" : "#ffffff"}
                  stroke="#10b981"
                  stroke-width="2.5"
                />
              {/each}
            {/if}
          </svg>

          <!-- Top HUD -->
          <div class="absolute top-2.5 left-3 flex items-center gap-2 text-[11px] font-mono bg-black/60 px-2.5 py-1 rounded-md border border-white/10">
            <span class="text-[#9ca3af]">Total Reach:</span>
            <span class="text-[#10b981] font-semibold">{studioStore.activeArtifact.reach_mm ?? 720} mm</span>
          </div>

          <div class="absolute bottom-2.5 right-3 text-[10px] text-[#6b7280]">
            6-DoF Forward Kinematics Chain
          </div>
        </div>

        <!-- Presets -->
        <div>
          <span class="text-[10px] uppercase font-semibold text-[#9ca3af] tracking-wider block mb-2">
            Robotic Poses:
          </span>
          <div class="grid grid-cols-2 gap-2">
            {#each ROBOTICS_PRESETS as preset}
              <button
                onclick={() => applyRoboticsPreset(preset.angles)}
                class="py-1.5 px-2.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-xs text-[#e2e8f0] text-center transition-all cursor-pointer"
              >
                {preset.label}
              </button>
            {/each}
          </div>
        </div>

        <!-- Tactile Joint Angle Sliders (Theta 1 to Theta 6) -->
        <div class="space-y-2.5 bg-[#0c0e14] p-3.5 rounded-xl border border-white/[0.06]">
          <span class="text-xs font-semibold text-white block mb-1">Joint Angle Actuators (Degrees):</span>
          {#each [0, 1, 2, 3, 4, 5] as jIdx}
            <div>
              <div class="flex justify-between text-[11px] text-[#9ca3af] mb-1">
                <span>Joint θ{jIdx + 1} {jIdx === 0 ? "(Base)" : jIdx === 1 ? "(Shoulder)" : jIdx === 2 ? "(Elbow)" : `(Wrist ${jIdx - 2})`}</span>
                <span class="font-mono text-[#10b981] font-semibold">{jointAngles[jIdx] ?? 0}°</span>
              </div>
              <input
                type="range"
                min="-180"
                max="180"
                step="5"
                value={jointAngles[jIdx] ?? 0}
                oninput={(e) => handleJointChange(jIdx, parseFloat((e.target as HTMLInputElement).value))}
                class="w-full accent-[#10b981] bg-white/10 h-1 rounded-lg appearance-none cursor-pointer"
              />
            </div>
          {/each}
        </div>

        <button
          onclick={downloadRoboticsJSON}
          class="w-full py-3 px-4 rounded-xl bg-white text-black font-semibold text-xs tracking-wide flex items-center justify-center gap-2 hover:bg-slate-200 transition-all shadow-lg cursor-pointer mt-auto"
        >
          <span>⬇ Export Kinematics Model (.json)</span>
        </button>
      </div>

    <!-- MODE 3: WAVEDROM DIGITAL TIMING -->
    {:else if studioStore.activeArtifact?.render_type === "wavedrom" || studioStore.activeArtifact?.tool === "wavedrom_generate"}
      <div class="p-5 flex-1 flex flex-col gap-4">
        <!-- Preset Protocol Chips -->
        <div>
          <span class="text-[10px] uppercase font-semibold text-[#9ca3af] tracking-wider block mb-2">
            Standard Bus Protocols:
          </span>
          <div class="grid grid-cols-4 gap-1.5">
            {#each WAVEDROM_PRESETS as p}
              <button
                onclick={() => applyWaveDromPreset(p.id)}
                class="py-1.5 px-2 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-[11px] text-[#e2e8f0] text-center transition-all cursor-pointer font-mono"
              >
                {p.label}
              </button>
            {/each}
          </div>
        </div>

        <!-- WaveDrom Viewport -->
        <div class="flex-1 bg-[#040508] p-4 rounded-xl border border-white/[0.08] overflow-x-auto flex flex-col items-center justify-center min-h-[260px]">
          <div bind:this={waveContainerEl} class="w-full overflow-x-auto"></div>
        </div>

        <button
          onclick={downloadWaveSVG}
          class="w-full py-3 px-4 rounded-xl bg-white text-black font-semibold text-xs tracking-wide flex items-center justify-center gap-2 hover:bg-slate-200 transition-all shadow-lg cursor-pointer mt-auto"
        >
          <span>⬇ Export Vector Waveform (.svg)</span>
        </button>
      </div>

    <!-- MODE 4: KICAD PCB NETLIST -->
    {:else if studioStore.activeArtifact?.kicad_netlist}
      <div class="p-5 flex-1 flex flex-col gap-4">
        <div>
          <h3 class="text-xs font-semibold uppercase tracking-wider text-[#9ca3af] mb-1">
            KiCad Electronic Netlist
          </h3>
          <p class="text-[11px] text-[#6b7280]">
            Generated circuit topology ready for PCB layout and routing.
          </p>
        </div>

        {#if studioStore.activeArtifact?.components}
          <div class="bg-[#0c0e14] p-3 rounded-xl border border-white/[0.06] text-xs">
            <span class="text-[#9ca3af] block mb-2 font-semibold">Bill of Materials (BOM):</span>
            <div class="space-y-1 font-mono text-[11px]">
              {#each studioStore.activeArtifact.components as c}
                <div class="flex justify-between border-b border-white/[0.04] py-0.5">
                  <span class="text-white font-bold">{c.ref} ({c.name})</span>
                  <span class="text-[#10b981]">{c.value} [{c.footprint}]</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <div class="flex-1 bg-black p-3 rounded-xl border border-white/[0.08] overflow-y-auto font-mono text-[11px] text-[#9ca3af]">
          <pre class="whitespace-pre-wrap">{studioStore.activeArtifact.kicad_netlist}</pre>
        </div>

        <button
          onclick={downloadNetlist}
          class="w-full py-3 px-4 rounded-xl bg-white text-black font-semibold text-xs tracking-wide flex items-center justify-center gap-2 hover:bg-slate-200 transition-all shadow-lg cursor-pointer mt-auto"
        >
          <span>⬇ Export KiCad Netlist (.net)</span>
        </button>
      </div>

    <!-- FALLBACK -->
    {:else}
      <div class="p-8 text-center text-[#9ca3af] text-xs">
        Select a STEM artifact, CAD model, or Robotics pose to view live parameters.
      </div>
    {/if}
  </div>
</aside>

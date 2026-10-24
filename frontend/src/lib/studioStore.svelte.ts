// studioStore.svelte.ts — Reactive state for the Side-by-Side STEM Engineering Studio
// Svelte 5 runes implementation for dual-pane workstation workflow.

export interface StudioArtifact {
  id: string;
  tool: string;
  render_type: string;
  title: string;
  shape?: string;
  parameters?: Record<string, any>;
  mesh?: {
    positions: number[];
    normals: number[];
  };
  stl_base64?: string;
  dimensions_mm?: Record<string, number>;
  triangle_count?: number;
  // PCB fields
  circuit_type?: string;
  kicad_netlist?: string;
  components?: any[];
  nets?: any[];
  // WaveDrom fields
  wavedrom_spec?: any;
  protocol?: string;
  // Robotics fields
  arm_type?: string;
  joint_angles_deg?: number[];
  end_effector?: { x: number; y: number; z: number };
  reach_mm?: number;
  joint_chain?: Array<{ x: number; y: number; z: number }>;
  metrics?: Array<{ label: string; value: string }>;
  // Silicon EDA fields
  module_name?: string;
  clock_domains?: string[];
  ports?: { inputs: string[]; outputs: string[] };
}

class StudioStore {
  activeArtifact = $state<StudioArtifact | null>(null);
  isOpen = $state<boolean>(false);

  open(artifact: StudioArtifact) {
    this.activeArtifact = artifact;
    this.isOpen = true;
  }

  close() {
    this.isOpen = false;
  }

  updateParameters(params: Record<string, any>, mesh?: any, stl_base64?: string) {
    if (this.activeArtifact) {
      this.activeArtifact.parameters = { ...this.activeArtifact.parameters, ...params };
      if (mesh) this.activeArtifact.mesh = mesh;
      if (stl_base64) this.activeArtifact.stl_base64 = stl_base64;
    }
  }

  updateRobotics(angles: number[], endEffector: any, reach: number, chain: any[], metrics?: any[]) {
    if (this.activeArtifact) {
      this.activeArtifact.joint_angles_deg = [...angles];
      this.activeArtifact.end_effector = endEffector;
      this.activeArtifact.reach_mm = reach;
      this.activeArtifact.joint_chain = chain;
      if (metrics) this.activeArtifact.metrics = metrics;
    }
  }

  updateWave(spec: any, protocol?: string) {
    if (this.activeArtifact) {
      this.activeArtifact.wavedrom_spec = spec;
      if (protocol) this.activeArtifact.protocol = protocol;
    }
  }
}

export const studioStore = new StudioStore();

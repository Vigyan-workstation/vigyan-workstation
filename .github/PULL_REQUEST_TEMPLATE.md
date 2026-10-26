## Description
<!-- Provide a brief description of changes, context, and motivation -->

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (addition of robotics kinematics, KiCad parser, WaveDrom, or SymPy model)
- [ ] Security enhancement (hardening air-gap verification, sanitization, sandbox)
- [ ] Performance optimization (VRAM reduction, AST parsing cache, UI responsiveness)
- [ ] Documentation / CI update

## Verification Checklist
- [ ] **Zero Telemetry / Air-Gap Maintained:** Validated that no remote URLs, CDNs, or external network calls are introduced.
- [ ] **Tests Pass:** Ran `pytest tests/` and verified all unit tests pass cleanly.
- [ ] **Frontend Build:** Compiled frontend via `cd frontend && bun run build` (if `frontend/src` was modified).
- [ ] **Demilitarized Civilian STEM:** Confirmed this code is strictly for peaceful educational, research, or civilian engineering use.
- [ ] **Contributor License Agreement (CLA):** By submitting this PR, I agree to the [ExperimentLab Contributor License Agreement](https://github.com/Vigyan-workstation/vigyan-workstation/blob/main/CONTRIBUTING.md#1-🛡️-contributor-license-agreement-cla--ip-ownership) and grant ExperimentLab AI sole, exclusive, irrevocable, and worldwide ownership of all intellectual property, copyright, and patent rights in this contribution.

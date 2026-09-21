# v0.42 retired P9 uninstall inventory

Safe ConceptGhost-owned P9-only runtime roots:
- %LOCALAPPDATA%\ConceptGhost-DepthProRuntime-v1
- %LOCALAPPDATA%\ConceptGhost-DepthAnythingRuntime-v1
- %LOCALAPPDATA%\ConceptGhost-SemanticAssist-v1

Keep for v0.42:
- ComfyUI Desktop / Python 3.13 environment
- ConceptGhost_Stage68
- Atlas Camera
- %LOCALAPPDATA%\ConceptGhost-MoGeRuntime-v1
- Atlas Depth Anything V2 metric model/cache
- Maya/mayapy
- NVIDIA/CUDA components required by retained runtimes

Optional/shared, remove only if unused elsewhere:
- ComfyUI-DepthAnythingV3
- comfy-env / pixi depthanythingv3-nodes environment
- ComfyUI-3D-Pack / pyhocon
- system Python / Python Launcher
- system Git

The v0.42 package includes AUDIT_RETIRED_P9_INSTALLS.bat and an ownership-marker-safe REMOVE_RETIRED_P9_RUNTIMES.bat.

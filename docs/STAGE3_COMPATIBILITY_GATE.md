# Stage 3 — Compatibility Gate

## Purpose

Enable Atlas's learned camera prior without disturbing the ComfyUI environment that already powers the user's working Single View and MultiView workflows.

## Evidence behind this stage

Atlas Camera's pinned `INSTALL.md` states that its core is clone-and-go, while the learned solve requires GeoCalib. For existing ComfyUI environments, Atlas explicitly warns that normal dependency resolution can replace Torch/NumPy-class dependencies and recommends a protected `--no-deps` route for GeoCalib. GeoCalib itself declares `torch`, `torchvision`, `opencv-python`, `kornia`, and `matplotlib`; its runtime image utilities import `cv2`, `kornia`, `numpy`, and `torch`.

The target environment already contains working Torch/Torchvision/NumPy/Kornia/Transformers. Therefore ConceptGhost treats those as immutable protected dependencies for Stage 3.

## Allowed writes

Only:

1. new GeoCalib distribution files, when GeoCalib is absent;
2. new `opencv-python` files, when no OpenCV distribution and no `cv2` module exist;
3. ConceptGhost manifests/logs/reports;
4. later, GeoCalib Torch Hub model-cache growth caused by the first actual learned solve.

## Forbidden behavior

- no `pip install -e .[neural]` into the shared ComfyUI environment;
- no dependency-resolving pip install for GeoCalib;
- no `--upgrade`;
- no Torch/Torchvision/NumPy/Kornia/Transformers/xformers changes;
- no edits to non-Atlas custom nodes;
- no edits to existing user workflow JSONs;
- no automatic replacement of a broken existing GeoCalib/OpenCV installation.

## Before/after gate

Before apply:

- full `pip freeze`;
- critical environment probe;
- metadata fingerprint of every non-Atlas item in `custom_nodes`;
- GeoCalib Torch Hub cache baseline.

After apply:

- full `pip freeze` again;
- environment probe again;
- non-Atlas `custom_nodes` fingerprint again;
- direct runtime import check of Torch/Torchvision/NumPy/Kornia/cv2/GeoCalib and Atlas `_require_geocalib()`.

Pass only if:

- every pre-existing pip package has exactly the same freeze line;
- no pre-existing package disappears;
- the only new packages are `geocalib` and/or `opencv-python`;
- every non-Atlas custom-node fingerprint is unchanged;
- the Atlas/GeoCalib runtime import probe succeeds.

Any violation stops the roadmap before the learned camera solve.

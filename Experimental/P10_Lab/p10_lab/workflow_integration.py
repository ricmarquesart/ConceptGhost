from __future__ import annotations

from copy import deepcopy

from .contracts import ContractError


_REFINED_EXPORT_ID = 1015
_EVIDENCE_NODE_ID = 2100


def integrate_gate4_refined_preview(workflow: dict) -> dict:
    """Add the Gate 4 P10 evidence node to the full ConceptGhost Master graph.

    The patch is intentionally surgical: it adds one downstream output node to
    the existing Refined/P9 export run_dir. Baseline nodes and links are not
    modified.
    """

    if not isinstance(workflow, dict):
        raise ContractError("Workflow must be a JSON object")
    patched = deepcopy(workflow)
    nodes = patched.get("nodes")
    links = patched.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        raise ContractError("Workflow must contain nodes and links arrays")
    if any(node.get("id") == _EVIDENCE_NODE_ID for node in nodes):
        raise ContractError("Gate 4 evidence node is already present")

    try:
        refined_export = next(node for node in nodes if node.get("id") == _REFINED_EXPORT_ID)
    except StopIteration as error:
        raise ContractError("Refined ConceptGhostExportBundle node 1015 is missing") from error
    if refined_export.get("type") != "ConceptGhostExportBundle":
        raise ContractError("Node 1015 is not the expected Refined ConceptGhostExportBundle")
    if "REFINED" not in str(refined_export.get("title") or "").upper():
        raise ContractError("Node 1015 is not labeled as the Refined branch")

    outputs = refined_export.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        raise ContractError("Refined export node has no outputs")
    run_dir_index = next(
        (index for index, output in enumerate(outputs) if output.get("name") == "run_dir"),
        None,
    )
    if run_dir_index is None:
        raise ContractError("Refined export node is missing run_dir output")

    next_link = max(
        int(patched.get("last_link_id") or 0) + 1,
        max((int(link[0]) for link in links if isinstance(link, list) and link), default=0) + 1,
    )
    node = {
        "id": _EVIDENCE_NODE_ID,
        "type": "ConceptGhostP10RefinedEvidencePreview",
        "pos": [9240, 8300],
        "size": [620, 520],
        "flags": {},
        "order": max((int(item.get("order") or 0) for item in nodes), default=0) + 1,
        "mode": 0,
        "inputs": [
            {"name": "run_dir", "type": "STRING", "link": next_link},
            {
                "name": "panorama_width",
                "type": "INT",
                "widget": {"name": "panorama_width"},
                "link": None,
            },
            {
                "name": "view_width",
                "type": "INT",
                "widget": {"name": "view_width"},
                "link": None,
            },
            {
                "name": "steps_per_segment",
                "type": "INT",
                "widget": {"name": "steps_per_segment"},
                "link": None,
            },
        ],
        "outputs": [
            {"name": "p9_3d_partial_erp", "type": "IMAGE", "links": None, "slot_index": 0},
            {"name": "source_authority_erp", "type": "IMAGE", "links": None, "slot_index": 1},
            {"name": "source_lock_mask", "type": "MASK", "links": None, "slot_index": 2},
            {"name": "flight_views", "type": "IMAGE", "links": None, "slot_index": 3},
            {"name": "hole_masks", "type": "MASK", "links": None, "slot_index": 4},
            {"name": "trajectory_map", "type": "IMAGE", "links": None, "slot_index": 5},
            {"name": "flight_gif_path", "type": "STRING", "links": None, "slot_index": 6},
            {"name": "control_manifest_path", "type": "STRING", "links": None, "slot_index": 7},
            {"name": "camera_manifest_path", "type": "STRING", "links": None, "slot_index": 8},
            {"name": "diagnostics_json", "type": "STRING", "links": None, "slot_index": 9},
        ],
        "properties": {"Node name for S&R": "ConceptGhostP10RefinedEvidencePreview"},
        "widgets_values": [1024, 640, 4],
        "title": "REFINED/P10 · 08 · VISUAL EVIDENCE · ERP + DRONE + HOLES",
    }
    nodes.append(node)
    links.append([next_link, _REFINED_EXPORT_ID, run_dir_index, _EVIDENCE_NODE_ID, 0, "STRING"])

    output_links = outputs[run_dir_index].get("links")
    if output_links is None:
        output_links = []
        outputs[run_dir_index]["links"] = output_links
    if next_link not in output_links:
        output_links.append(next_link)

    patched["last_node_id"] = _EVIDENCE_NODE_ID
    patched["last_link_id"] = next_link

    for item in nodes:
        if item.get("id") == 68:
            item["title"] = (
                "01 · RUN MODE · v1.54 P10 PREVIEW · "
                "Baseline/P9 · Refined/P9+P10 Evidence"
            )
        elif item.get("id") == 2:
            item["title"] = (
                "01 · MASTER CONTROLS · v1.54 P10 GATE4 PREVIEW · "
                "BASELINE + REFINED"
            )
    return patched



def integrate_gate5_refined_preview(workflow: dict) -> dict:
    """Build the full Gate 5 Refined graph from the proven Master workflow.

    Gate 5 keeps Baseline untouched. It first applies the Gate 4 evidence patch,
    then appends a compact WAN I2V chain and one sequential ConceptGhost sampler.
    The sampler consumes the live flight views, raw hole masks and control
    manifest emitted by P10; no duplicated sampler graph is required per mission.
    """

    patched = integrate_gate4_refined_preview(workflow)
    nodes = patched["nodes"]
    links = patched["links"]
    by_id = {node.get("id"): node for node in nodes}
    evidence = by_id[_EVIDENCE_NODE_ID]

    reserved_ids = set(range(2200, 2209))
    if any(node.get("id") in reserved_ids for node in nodes):
        raise ContractError("Gate 5 reserved node ids already exist")

    next_link = max(
        int(patched.get("last_link_id") or 0) + 1,
        max((int(link[0]) for link in links if isinstance(link, list) and link), default=0) + 1,
    )

    def add_node(node):
        nodes.append(node)

    def ensure_output_links(node, slot):
        output = node["outputs"][slot]
        if output.get("links") is None:
            output["links"] = []
        return output["links"]

    def connect(source_id, source_slot, target_id, target_slot, type_name):
        nonlocal next_link
        link_id = next_link
        next_link += 1
        links.append([link_id, source_id, source_slot, target_id, target_slot, type_name])
        ensure_output_links(by_id[source_id], source_slot).append(link_id)
        target = by_id[target_id]
        target["inputs"][target_slot]["link"] = link_id
        return link_id

    order = max((int(node.get("order") or 0) for node in nodes), default=0)

    node_defs = [
        {
            "id": 2200,
            "type": "UNETLoader",
            "pos": [10040, 8200],
            "size": [430, 90],
            "flags": {},
            "order": order + 1,
            "mode": 0,
            "inputs": [],
            "outputs": [{"name": "MODEL", "type": "MODEL", "links": None, "slot_index": 0}],
            "properties": {"Node name for S&R": "UNETLoader"},
            "widgets_values": [
                "wan\\wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors",
                "default",
            ],
            "title": "REFINED/P10 · WAN 11GB · I2V FP8",
        },
        {
            "id": 2201,
            "type": "LoraLoaderModelOnly",
            "pos": [10040, 8320],
            "size": [430, 82],
            "flags": {},
            "order": order + 2,
            "mode": 0,
            "inputs": [{"name": "model", "type": "MODEL", "link": None}],
            "outputs": [{"name": "MODEL", "type": "MODEL", "links": None, "slot_index": 0}],
            "properties": {"Node name for S&R": "LoraLoaderModelOnly"},
            "widgets_values": [
                "wan\\lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16.safetensors",
                1.0,
            ],
            "title": "REFINED/P10 · WAN · LIGHTX2V 4-STEP",
        },
        {
            "id": 2202,
            "type": "ModelSamplingSD3",
            "pos": [10040, 8430],
            "size": [430, 58],
            "flags": {},
            "order": order + 3,
            "mode": 0,
            "inputs": [{"name": "model", "type": "MODEL", "link": None}],
            "outputs": [{"name": "MODEL", "type": "MODEL", "links": None, "slot_index": 0}],
            "properties": {"Node name for S&R": "ModelSamplingSD3"},
            "widgets_values": [5.0],
            "title": "REFINED/P10 · WAN · SHIFT 5",
        },
        {
            "id": 2203,
            "type": "CLIPLoader",
            "pos": [10040, 8530],
            "size": [430, 106],
            "flags": {},
            "order": order + 4,
            "mode": 0,
            "inputs": [],
            "outputs": [{"name": "CLIP", "type": "CLIP", "links": None, "slot_index": 0}],
            "properties": {"Node name for S&R": "CLIPLoader"},
            "widgets_values": [
                "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                "wan",
                "default",
            ],
            "title": "REFINED/P10 · WAN · UMT5",
        },
        {
            "id": 2204,
            "type": "CLIPTextEncode",
            "pos": [10520, 8500],
            "size": [460, 125],
            "flags": {},
            "order": order + 5,
            "mode": 0,
            "inputs": [{"name": "clip", "type": "CLIP", "link": None}],
            "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": None, "slot_index": 0}],
            "properties": {"Node name for S&R": "CLIPTextEncode"},
            "widgets_values": [
                "A coherent high quality continuation of the same scene, consistent architecture and geometry, stable camera motion, detailed realistic surfaces."
            ],
            "title": "REFINED/P10 · WAN · POSITIVE",
        },
        {
            "id": 2205,
            "type": "CLIPTextEncode",
            "pos": [10520, 8650],
            "size": [460, 125],
            "flags": {},
            "order": order + 6,
            "mode": 0,
            "inputs": [{"name": "clip", "type": "CLIP", "link": None}],
            "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": None, "slot_index": 0}],
            "properties": {"Node name for S&R": "CLIPTextEncode"},
            "widgets_values": [
                "low quality, distortion, unstable geometry, inconsistent structure, flicker, artifacts, warped architecture"
            ],
            "title": "REFINED/P10 · WAN · NEGATIVE",
        },
        {
            "id": 2206,
            "type": "VAELoader",
            "pos": [10040, 8670],
            "size": [430, 60],
            "flags": {},
            "order": order + 7,
            "mode": 0,
            "inputs": [],
            "outputs": [{"name": "VAE", "type": "VAE", "links": None, "slot_index": 0}],
            "properties": {"Node name for S&R": "VAELoader"},
            "widgets_values": ["wan_2.1_vae.safetensors"],
            "title": "REFINED/P10 · WAN · VAE",
        },
        {
            "id": 2207,
            "type": "ConceptGhostP10WanSequentialSampler",
            "pos": [11100, 8260],
            "size": [650, 520],
            "flags": {},
            "order": order + 8,
            "mode": 0,
            "inputs": [
                {"name": "model", "type": "MODEL", "link": None},
                {"name": "positive", "type": "CONDITIONING", "link": None},
                {"name": "negative", "type": "CONDITIONING", "link": None},
                {"name": "vae", "type": "VAE", "link": None},
                {"name": "control_video", "type": "IMAGE", "link": None},
                {"name": "hole_mask", "type": "MASK", "link": None},
                {"name": "control_manifest_path", "type": "STRING", "link": None},
                {"name": "seed", "type": "INT", "widget": {"name": "seed"}, "link": None},
                {"name": "width", "type": "INT", "widget": {"name": "width"}, "link": None},
                {"name": "height", "type": "INT", "widget": {"name": "height"}, "link": None},
                {"name": "max_window_length", "type": "INT", "widget": {"name": "max_window_length"}, "link": None},
                {"name": "steps", "type": "INT", "widget": {"name": "steps"}, "link": None},
                {"name": "cfg", "type": "FLOAT", "widget": {"name": "cfg"}, "link": None},
            ],
            "outputs": [
                {"name": "composite_preview", "type": "IMAGE", "links": None, "slot_index": 0},
                {"name": "generated_dir", "type": "STRING", "links": None, "slot_index": 1},
                {"name": "wan_manifest_path", "type": "STRING", "links": None, "slot_index": 2},
                {"name": "diagnostics_json", "type": "STRING", "links": None, "slot_index": 3},
            ],
            "properties": {"Node name for S&R": "ConceptGhostP10WanSequentialSampler"},
            "widgets_values": [0, 832, 480, 33, 4, 1.0],
            "title": "REFINED/P10 · 09 · SEQUENTIAL WAN + SOURCE-PRESERVING COMPOSITE",
        },
        {
            "id": 2208,
            "type": "PreviewImage",
            "pos": [11820, 8260],
            "size": [520, 420],
            "flags": {},
            "order": order + 9,
            "mode": 0,
            "inputs": [{"name": "images", "type": "IMAGE", "link": None}],
            "outputs": [],
            "properties": {"Node name for S&R": "PreviewImage"},
            "widgets_values": [],
            "title": "P10 LIVE · WAN FILLED + P9 PRESERVED",
        },
    ]

    for node in node_defs:
        add_node(node)
        by_id[node["id"]] = node

    connect(2200, 0, 2201, 0, "MODEL")
    connect(2201, 0, 2202, 0, "MODEL")
    connect(2203, 0, 2204, 0, "CLIP")
    connect(2203, 0, 2205, 0, "CLIP")
    connect(2202, 0, 2207, 0, "MODEL")
    connect(2204, 0, 2207, 1, "CONDITIONING")
    connect(2205, 0, 2207, 2, "CONDITIONING")
    connect(2206, 0, 2207, 3, "VAE")
    connect(_EVIDENCE_NODE_ID, 3, 2207, 4, "IMAGE")
    connect(_EVIDENCE_NODE_ID, 4, 2207, 5, "MASK")
    connect(_EVIDENCE_NODE_ID, 7, 2207, 6, "STRING")
    connect(2207, 0, 2208, 0, "IMAGE")

    patched["last_node_id"] = 2208
    patched["last_link_id"] = next_link - 1

    for item in nodes:
        if item.get("id") == 68:
            item["title"] = (
                "01 · RUN MODE · v1.54 P10 GATE5 · "
                "Baseline/P9 · Refined/P9+P10 WAN"
            )
        elif item.get("id") == 2:
            item["title"] = (
                "01 · MASTER CONTROLS · v1.54 P10 GATE5 · "
                "BASELINE + REFINED WAN COMPLETION"
            )

    return patched

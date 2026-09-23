from __future__ import annotations

from copy import deepcopy

from .contracts import ContractError


_REFINED_EXPORT_ID = 1015
_EVIDENCE_NODE_ID = 2100
_ROUTE_AUTHOR_NODE_ID = 2099
_DEFAULT_GEOMETRY_PROFILE = "High Fidelity Split Clean"

# Dedicated P10 visual lane below the existing Refined/P9 graph.
# These positions intentionally leave the proven v1.53 Baseline/Refined layout
# untouched while arranging Gate 4 -> Gate 5 -> Gate 6 left-to-right.
_P10_LAYOUT_POSITIONS = {
    2097: (8720, 9300),
    2098: (9480, 9520),
    2099: (9460, 9600),
    2110: (10220, 9600),
    2100: (10200, 10000),
    2101: (10900, 9600),
    2102: (11320, 9600),
    2103: (10900, 9950),
    2104: (11220, 9950),
    2105: (11740, 9600),
    2106: (10900, 10300),
    2107: (11220, 10300),
    2108: (11640, 9950),
    2200: (12600, 9600),
    2201: (12600, 9720),
    2202: (12600, 9830),
    2203: (12600, 9930),
    2204: (13090, 9930),
    2205: (13090, 10080),
    2206: (12600, 10070),
    2207: (13620, 9600),
    2208: (14330, 9600),
    2300: (14910, 9600),
    2301: (15650, 9600),
}


def apply_p10_master_defaults(workflow: dict) -> dict:
    """Apply release-facing P10 defaults without changing runtime authority rules.

    The existing ConceptGhost MasterConfig serializes widgets in the order:
    scene_name, preset, camera_mode, moge_version, geometry_profile,
    extra_diagnostics, output_root. P10 release workflows default to
    High Fidelity Split Clean, while the artist can still override it manually.
    """
    nodes = workflow.get("nodes") if isinstance(workflow, dict) else None
    if not isinstance(nodes, list):
        raise ContractError("Workflow must contain a nodes array")
    master = next(
        (
            node for node in nodes
            if node.get("id") == 2 and node.get("type") == "ConceptGhostMasterConfig"
        ),
        None,
    )
    if master is None:
        return workflow
    values = master.get("widgets_values")
    if not isinstance(values, list) or len(values) < 5:
        raise ContractError("ConceptGhostMasterConfig widgets are incomplete")
    values[4] = _DEFAULT_GEOMETRY_PROFILE
    return workflow


def organize_p10_layout(workflow: dict) -> dict:
    """Move known P10 nodes into a dedicated non-overlapping visual lane.

    This is layout-only: node ids, links, values, modes and execution semantics
    remain unchanged. Unknown/future nodes are not moved automatically.
    """
    nodes = workflow.get("nodes") if isinstance(workflow, dict) else None
    if not isinstance(nodes, list):
        raise ContractError("Workflow must contain a nodes array")
    for node in nodes:
        node_id = node.get("id")
        if node_id in _P10_LAYOUT_POSITIONS:
            node["pos"] = list(_P10_LAYOUT_POSITIONS[node_id])
    return workflow


def integrate_gate4_refined_preview(workflow: dict) -> dict:
    """Add the Gate 4 P10 evidence node to the full ConceptGhost Master graph.

    The patch is intentionally surgical: it adds one downstream output node to
    the existing Refined/P9 export run_dir. Baseline nodes and links are not
    modified.
    """

    if not isinstance(workflow, dict):
        raise ContractError("Workflow must be a JSON object")
    patched = deepcopy(workflow)
    apply_p10_master_defaults(patched)
    nodes = patched.get("nodes")
    links = patched.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        raise ContractError("Workflow must contain nodes and links arrays")
    if any(node.get("id") in {_ROUTE_AUTHOR_NODE_ID, _EVIDENCE_NODE_ID} for node in nodes):
        raise ContractError("Gate 4 route/evidence nodes are already present")

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
    route_author = {
        "id": _ROUTE_AUTHOR_NODE_ID,
        "type": "ConceptGhostP10DroneRouteAuthoring",
        "pos": list(_P10_LAYOUT_POSITIONS[_ROUTE_AUTHOR_NODE_ID]),
        "size": [700, 720],
        "flags": {},
        "order": max((int(item.get("order") or 0) for item in nodes), default=0) + 1,
        "mode": 0,
        "inputs": [
            {"name": "run_dir", "type": "STRING", "link": next_link},
            {
                "name": "route_plan_json",
                "type": "STRING",
                "widget": {"name": "route_plan_json"},
                "link": None,
            },
            {
                "name": "frames_per_drone",
                "type": "INT",
                "widget": {"name": "frames_per_drone"},
                "link": None,
            },
            {
                "name": "min_clearance_m",
                "type": "FLOAT",
                "widget": {"name": "min_clearance_m"},
                "link": None,
            },
        ],
        "outputs": [
            {"name": "route_workspace", "type": "IMAGE", "links": None, "slot_index": 0},
            {"name": "route_plan_json", "type": "STRING", "links": None, "slot_index": 1},
            {"name": "projection_json", "type": "STRING", "links": None, "slot_index": 2},
            {"name": "diagnostics_json", "type": "STRING", "links": None, "slot_index": 3},
        ],
        "properties": {"Node name for S&R": "ConceptGhostP10DroneRouteAuthoring"},
        "widgets_values": ["", 30, 0.20],
        "title": "REFINED/P10 · 07R · ARTIST DRONE ROUTES · PERSPECTIVE + TOP + SIDE + FRONT",
    }
    nodes.append(route_author)
    links.append([next_link, _REFINED_EXPORT_ID, run_dir_index, _ROUTE_AUTHOR_NODE_ID, 0, "STRING"])
    route_run_link = next_link
    next_link += 1

    node = {
        "id": _EVIDENCE_NODE_ID,
        "type": "ConceptGhostP10RefinedEvidencePreview",
        "pos": list(_P10_LAYOUT_POSITIONS[2100]),
        "size": [620, 520],
        "flags": {},
        "order": max((int(item.get("order") or 0) for item in nodes), default=0) + 1,
        "mode": 0,
        "inputs": [
            {"name": "run_dir", "type": "STRING", "link": None},
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
            {
                "name": "route_plan_json",
                "type": "STRING",
                "link": next_link,
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
    route_plan_link = next_link
    links.append([route_plan_link, _ROUTE_AUTHOR_NODE_ID, 1, _EVIDENCE_NODE_ID, 4, "STRING"])
    route_author["outputs"][1]["links"] = [route_plan_link]
    next_link += 1
    evidence_run_link = next_link
    node["inputs"][0]["link"] = evidence_run_link
    links.append([evidence_run_link, _REFINED_EXPORT_ID, run_dir_index, _EVIDENCE_NODE_ID, 0, "STRING"])

    output_links = outputs[run_dir_index].get("links")
    if output_links is None:
        output_links = []
        outputs[run_dir_index]["links"] = output_links
    for link_id in (route_run_link, evidence_run_link):
        if link_id not in output_links:
            output_links.append(link_id)

    patched["last_node_id"] = _EVIDENCE_NODE_ID
    patched["last_link_id"] = evidence_run_link

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
            "pos": list(_P10_LAYOUT_POSITIONS[2200]),
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
            "pos": list(_P10_LAYOUT_POSITIONS[2201]),
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
            "pos": list(_P10_LAYOUT_POSITIONS[2202]),
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
            "pos": list(_P10_LAYOUT_POSITIONS[2203]),
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
            "pos": list(_P10_LAYOUT_POSITIONS[2204]),
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
            "pos": list(_P10_LAYOUT_POSITIONS[2205]),
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
            "pos": list(_P10_LAYOUT_POSITIONS[2206]),
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
            "pos": list(_P10_LAYOUT_POSITIONS[2207]),
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
                {"name": "clip_vision_output", "type": "CLIP_VISION_OUTPUT", "link": None},
                {"name": "wan_seed", "type": "INT", "widget": {"name": "wan_seed"}, "link": None},
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
                {"name": "drone_preview_index_path", "type": "STRING", "links": None, "slot_index": 4},
            ],
            "properties": {"Node name for S&R": "ConceptGhostP10WanSequentialSampler"},
            "widgets_values": [0, 832, 480, 33, 4, 1.0],
            "title": "REFINED/P10 · 09 · SEQUENTIAL WAN + SOURCE-PRESERVING COMPOSITE",
        },
        {
            "id": 2208,
            "type": "PreviewImage",
            "pos": list(_P10_LAYOUT_POSITIONS[2208]),
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



def integrate_gate6_refined_preview(workflow: dict) -> dict:
    """Extend the full Refined Gate 5 graph with known-camera reconstruction.

    The reconstruction node consumes only Gate 5's WAN manifest plus Gate 4/6.1
    camera manifest. Baseline remains untouched. One PreviewImage exposes the
    pre-fusion mesh reconstruction visually inside the same Master workflow.
    """

    patched = integrate_gate5_refined_preview(workflow)
    nodes = patched["nodes"]
    links = patched["links"]
    by_id = {node.get("id"): node for node in nodes}

    if 2300 in by_id or 2301 in by_id:
        raise ContractError("Gate 6 reserved node ids already exist")
    if _EVIDENCE_NODE_ID not in by_id or 2207 not in by_id:
        raise ContractError("Gate 6 requires Gate 4 evidence and Gate 5 WAN sampler")

    next_link = max(
        int(patched.get("last_link_id") or 0) + 1,
        max((int(link[0]) for link in links if isinstance(link, list) and link), default=0) + 1,
    )

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
        by_id[target_id]["inputs"][target_slot]["link"] = link_id
        return link_id

    order = max((int(node.get("order") or 0) for node in nodes), default=0)

    reconstruction = {
        "id": 2300,
        "type": "ConceptGhostP10ReconstructionRuntime",
        "pos": list(_P10_LAYOUT_POSITIONS[2300]),
        "size": [680, 390],
        "flags": {},
        "order": order + 1,
        "mode": 0,
        "inputs": [
            {"name": "wan_manifest_path", "type": "STRING", "link": None},
            {"name": "camera_manifest_path", "type": "STRING", "link": None},
            {
                "name": "resume_existing",
                "type": "BOOLEAN",
                "widget": {"name": "resume_existing"},
                "link": None,
            },
            {
                "name": "colmap_executable",
                "type": "STRING",
                "widget": {"name": "colmap_executable"},
                "link": None,
            },
        ],
        "outputs": [
            {"name": "mesh_preview", "type": "IMAGE", "links": None, "slot_index": 0},
            {"name": "pre_fusion_mesh", "type": "STRING", "links": None, "slot_index": 1},
            {"name": "gate6_output_root", "type": "STRING", "links": None, "slot_index": 2},
            {"name": "runtime_manifest_path", "type": "STRING", "links": None, "slot_index": 3},
            {"name": "diagnostics_json", "type": "STRING", "links": None, "slot_index": 4},
        ],
        "properties": {"Node name for S&R": "ConceptGhostP10ReconstructionRuntime"},
        "widgets_values": [True, ""],
        "title": "REFINED/P10 · 10 · KNOWN-CAMERA RECONSTRUCTION · SPARSE + DENSE + MESH",
    }

    preview = {
        "id": 2301,
        "type": "PreviewImage",
        "pos": list(_P10_LAYOUT_POSITIONS[2301]),
        "size": [560, 430],
        "flags": {},
        "order": order + 2,
        "mode": 0,
        "inputs": [{"name": "images", "type": "IMAGE", "link": None}],
        "outputs": [],
        "properties": {"Node name for S&R": "PreviewImage"},
        "widgets_values": [],
        "title": "P10 LIVE · RECONSTRUCTED PRE-FUSION MESH",
    }

    nodes.extend((reconstruction, preview))
    by_id[2300] = reconstruction
    by_id[2301] = preview

    connect(2207, 2, 2300, 0, "STRING")
    connect(_EVIDENCE_NODE_ID, 8, 2300, 1, "STRING")
    connect(2300, 0, 2301, 0, "IMAGE")

    patched["last_node_id"] = 2301
    patched["last_link_id"] = next_link - 1

    for item in nodes:
        if item.get("id") == 68:
            item["title"] = (
                "01 · RUN MODE · v1.54 P10 GATE6 · "
                "Baseline/P9 · Refined/P9+P10 WAN+RECONSTRUCTION"
            )
        elif item.get("id") == 2:
            item["title"] = (
                "01 · MASTER CONTROLS · v1.54 P10 GATE6 · "
                "BASELINE + REFINED WAN + KNOWN-CAMERA 3D"
            )

    organize_p10_layout(patched)
    return patched



def _remove_links_touching_nodes(workflow: dict, removed_node_ids: set[int]) -> None:
    """Remove links to/from removed nodes and repair remaining slot link arrays."""

    nodes=workflow["nodes"]
    links=workflow["links"]
    kept=[
        link for link in links
        if isinstance(link,list)
        and len(link)>=6
        and int(link[1]) not in removed_node_ids
        and int(link[3]) not in removed_node_ids
    ]
    workflow["links"]=kept
    kept_ids={int(link[0]) for link in kept}
    for node in nodes:
        for output in node.get("outputs") or []:
            values=output.get("links")
            if isinstance(values,list):
                output["links"]=[int(value) for value in values if int(value) in kept_ids] or None
        for input_slot in node.get("inputs") or []:
            value=input_slot.get("link")
            if value is not None and int(value) not in kept_ids:
                input_slot["link"]=None


def integrate_route_setup_refined_preview(workflow: dict) -> dict:
    """Stage A: solve P9 once, expose the route workspace, commit route, stop.

    This deliberately contains no WAN or Gate-6 node. The first Queue Prompt
    reaches the editable P9 route workspace. After artist editing, a second
    lightweight Queue Prompt commits a scene-bound production_entry.json while
    P9 remains cached/unchanged.
    """

    patched=integrate_gate4_refined_preview(workflow)
    nodes=patched["nodes"]
    by_id={node.get("id"):node for node in nodes}
    if _EVIDENCE_NODE_ID not in by_id or _ROUTE_AUTHOR_NODE_ID not in by_id:
        raise ContractError("Route Setup requires integrated route/evidence nodes")

    nodes[:]=[node for node in nodes if node.get("id")!=_EVIDENCE_NODE_ID]
    _remove_links_touching_nodes(patched,{_EVIDENCE_NODE_ID})
    by_id={node.get("id"):node for node in nodes}

    refined_export=by_id[_REFINED_EXPORT_ID]
    run_dir_index=next(
        index for index,output in enumerate(refined_export["outputs"])
        if output.get("name")=="run_dir"
    )
    next_link=max(
        int(patched.get("last_link_id") or 0)+1,
        max((int(link[0]) for link in patched["links"]),default=0)+1,
    )
    order=max((int(node.get("order") or 0) for node in nodes),default=0)

    guide_text=(
        "WORKFLOW 01 — ROUTE SETUP\n\n"
        "RUN #1: clique Run uma vez para resolver/carregar o P9 e abrir o workspace de drones. "
        "Este workflow PARA antes de WAN/Gate6. WAITING_FOR_ARTIST_ROUTE é esperado.\n\n"
        "EDITE: use Perspective para inspeção e TOP/SIDE/FRONT para posicionar waypoints/alvo.\n\n"
        "RUN #2: depois de editar, clique Run novamente NESTE MESMO workflow. "
        "O P9 deve ficar em cache; a rota é commitada como ARTIST_AUTHORED.\n\n"
        "Somente quando o commit mostrar READY / production_ready=true, abra "
        "02_ConceptGhost_P10_PRODUCTION_r7.json."
    )
    guide={
        "id":2097,
        "type":"ConceptGhostP10WorkflowInstructions",
        "pos":list(_P10_LAYOUT_POSITIONS[2097]),
        "size":[760,360],
        "flags":{},
        "order":order+2,
        "mode":0,
        "inputs":[{
            "name":"instructions",
            "type":"STRING",
            "widget":{"name":"instructions"},
            "link":None,
        }],
        "outputs":[{"name":"instructions","type":"STRING","links":None,"slot_index":0}],
        "properties":{"Node name for S&R":"ConceptGhostP10WorkflowInstructions"},
        "widgets_values":[guide_text],
        "title":"01 · START HERE · RUN #1 → EDIT DRONES → RUN #2 COMMIT",
    }
    nodes.append(guide)

    commit={
        "id":2110,
        "type":"ConceptGhostP10RouteCommit",
        "pos":list(_P10_LAYOUT_POSITIONS[2110]),
        "size":[600,220],
        "flags":{},
        "order":order+1,
        "mode":0,
        "inputs":[
            {"name":"run_dir","type":"STRING","link":next_link},
            {"name":"route_plan_json","type":"STRING","link":next_link+1},
        ],
        "outputs":[
            {"name":"production_entry_path","type":"STRING","links":None,"slot_index":0},
            {"name":"diagnostics_json","type":"STRING","links":None,"slot_index":1},
        ],
        "properties":{"Node name for S&R":"ConceptGhostP10RouteCommit"},
        "widgets_values":[],
        "title":"01 · STEP 3 · RUN #2 COMMIT · READY THEN OPEN WORKFLOW 02",
    }
    nodes.append(commit)

    patched["links"].append([
        next_link,_REFINED_EXPORT_ID,run_dir_index,2110,0,"STRING"
    ])
    output_links=refined_export["outputs"][run_dir_index].get("links")
    if output_links is None:
        output_links=[]
        refined_export["outputs"][run_dir_index]["links"]=output_links
    output_links.append(next_link)

    route_author=by_id[_ROUTE_AUTHOR_NODE_ID]
    patched["links"].append([
        next_link+1,_ROUTE_AUTHOR_NODE_ID,1,2110,1,"STRING"
    ])
    if route_author["outputs"][1].get("links") is None:
        route_author["outputs"][1]["links"]=[]
    route_author["outputs"][1]["links"].append(next_link+1)

    patched["last_node_id"]=2110
    patched["last_link_id"]=next_link+1
    for item in nodes:
        if item.get("id")==68:
            item["title"]="01 · ROUTE SETUP · RUN #1 P9 / RUN #2 COMMIT · NO WAN"
        elif item.get("id")==2:
            item["title"]="01 · P9 MASTER CONTROLS · UPSTREAM AUTHORITY"
        elif item.get("id")==_ROUTE_AUTHOR_NODE_ID:
            item["title"]="01 · STEP 2 · EDIT DRONES · PERSPECTIVE + TOP + SIDE + FRONT"
    patched["extra"]=patched.get("extra") or {}
    patched["extra"]["conceptghost"]={
        **(patched["extra"].get("conceptghost") or {}),
        "workflow_number":"01",
        "workflow_role":"P10_ROUTE_SETUP",
        "queue_sequence":["RUN_1_P9_AND_WORKSPACE","ARTIST_EDIT","RUN_2_COMMIT_ROUTE"],
        "stops_before_wan_gate6":True,
    }
    organize_p10_layout(patched)
    return patched


def integrate_p10_production_from_entry(workflow: dict) -> dict:
    """Stage B: a standalone P10 graph loaded from a committed Stage-A entry.

    The resulting workflow has no Baseline/P9 solver dependency. It consumes the
    immutable P9 run_dir and artist route recorded by Route Setup, then executes
    Evidence -> WAN -> known-camera reconstruction.
    """

    full=integrate_gate6_refined_preview(workflow)
    keep_ids={_EVIDENCE_NODE_ID,*range(2200,2209),2300,2301}
    kept_nodes=[node for node in full["nodes"] if node.get("id") in keep_ids]
    kept_links=[
        link for link in full["links"]
        if int(link[1]) in keep_ids and int(link[3]) in keep_ids
    ]
    kept_link_ids={int(link[0]) for link in kept_links}
    for node in kept_nodes:
        for input_slot in node.get("inputs") or []:
            value=input_slot.get("link")
            if value is not None and int(value) not in kept_link_ids:
                input_slot["link"]=None
        for output in node.get("outputs") or []:
            values=output.get("links")
            if isinstance(values,list):
                output["links"]=[int(value) for value in values if int(value) in kept_link_ids] or None

    by_id={node.get("id"):node for node in kept_nodes}
    if _EVIDENCE_NODE_ID not in by_id:
        raise ContractError("P10 Production workflow lost evidence node")

    production_guide_text=(
        "WORKFLOW 02 — P10 PRODUCTION\n\n"
        "Pré-requisito: Workflow 01 terminou o RUN #2 com READY / production_ready=true.\n\n"
        "Deixe production_entry_path = AUTO_LATEST para o fluxo normal. "
        "Ao executar, o loader mostra o caminho absoluto do production_entry.json, "
        "committed_route.json e P9 run_dir usados.\n\n"
        "RUN #3: clique Run UMA VEZ. Este workflow NÃO contém solver P9. "
        "Ele executa Evidence → WAN → Reconstruction → Geometry Quality.\n\n"
        "Cada novo Run cria outro p10_attempt_id e não sobrescreve a tentativa anterior."
    )
    production_guide={
        "id":2097,
        "type":"ConceptGhostP10WorkflowInstructions",
        "pos":list(_P10_LAYOUT_POSITIONS[2097]),
        "size":[760,330],
        "flags":{},
        "order":0,
        "mode":0,
        "inputs":[{
            "name":"instructions",
            "type":"STRING",
            "widget":{"name":"instructions"},
            "link":None,
        }],
        "outputs":[{"name":"instructions","type":"STRING","links":None,"slot_index":0}],
        "properties":{"Node name for S&R":"ConceptGhostP10WorkflowInstructions"},
        "widgets_values":[production_guide_text],
        "title":"02 · START HERE · AUTO_LATEST → RUN #3 P10 PRODUCTION",
    }
    kept_nodes.append(production_guide)

    loader={
        "id":2098,
        "type":"ConceptGhostP10ProductionEntryLoader",
        "pos":list(_P10_LAYOUT_POSITIONS[2098]),
        "size":[660,210],
        "flags":{},
        "order":1,
        "mode":0,
        "inputs":[
            {
                "name":"production_entry_path",
                "type":"STRING",
                "widget":{"name":"production_entry_path"},
                "link":None,
            }
        ],
        "outputs":[
            {"name":"run_dir","type":"STRING","links":None,"slot_index":0},
            {"name":"route_plan_json","type":"STRING","links":None,"slot_index":1},
            {"name":"p10_attempt_root","type":"STRING","links":None,"slot_index":2},
            {"name":"p10_attempt_id","type":"STRING","links":None,"slot_index":3},
            {"name":"diagnostics_json","type":"STRING","links":None,"slot_index":4},
        ],
        "properties":{"Node name for S&R":"ConceptGhostP10ProductionEntryLoader"},
        "widgets_values":["AUTO_LATEST"],
        "title":"02 · STEP 1 · AUTO_LATEST HANDOFF · PATHS SHOWN AFTER RUN",
    }
    kept_nodes.append(loader)
    by_id[2098]=loader

    next_link=max((int(link[0]) for link in kept_links),default=0)+1
    evidence=by_id[_EVIDENCE_NODE_ID]
    run_input=next(index for index,item in enumerate(evidence["inputs"]) if item.get("name")=="run_dir")
    route_input=next(index for index,item in enumerate(evidence["inputs"]) if item.get("name")=="route_plan_json")
    attempt_input=next(
        (index for index,item in enumerate(evidence["inputs"]) if item.get("name")=="p10_attempt_root"),
        None,
    )
    if attempt_input is None:
        attempt_input=len(evidence["inputs"])
        evidence["inputs"].append({
            "name":"p10_attempt_root",
            "type":"STRING",
            "link":None,
        })
    evidence["inputs"][run_input]["link"]=next_link
    evidence["inputs"][route_input]["link"]=next_link+1
    evidence["inputs"][attempt_input]["link"]=next_link+2
    kept_links.extend([
        [next_link,2098,0,_EVIDENCE_NODE_ID,run_input,"STRING"],
        [next_link+1,2098,1,_EVIDENCE_NODE_ID,route_input,"STRING"],
        [next_link+2,2098,2,_EVIDENCE_NODE_ID,attempt_input,"STRING"],
    ])
    loader["outputs"][0]["links"]=[next_link]
    loader["outputs"][1]["links"]=[next_link+1]
    loader["outputs"][2]["links"]=[next_link+2]

    full["nodes"]=kept_nodes
    full["links"]=kept_links
    full["last_node_id"]=2301
    full["last_link_id"]=next_link+2
    full["groups"]=[]
    for item in kept_nodes:
        if item.get("id")==_EVIDENCE_NODE_ID:
            item["title"]="02 · STEP 2 · P10 EVIDENCE · COMMITTED ROUTE + P9 RUN"
        elif item.get("id")==2207:
            item["title"]="02 · STEP 3 · WAN + SOURCE-PRESERVING COMPOSITE"
        elif item.get("id")==2300:
            item["title"]="02 · STEP 4 · KNOWN-CAMERA RECONSTRUCTION + GEOMETRY QUALITY"
        elif item.get("id")==2301:
            item["title"]="02 · RESULT · RECONSTRUCTED PRE-FUSION MESH"

    full["extra"]={
        "conceptghost":{
            "workflow_number":"02",
            "workflow_role":"P10_PRODUCTION_FROM_EXISTING_P9",
            "p9_solver_present":False,
            "requires_production_entry":True,
            "normal_loader_mode":"AUTO_LATEST",
            "queue_sequence":["RUN_3_P10_PRODUCTION"],
        }
    }
    organize_p10_layout(full)
    return full

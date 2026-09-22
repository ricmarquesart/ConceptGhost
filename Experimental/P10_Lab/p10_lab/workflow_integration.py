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
            {"name": "diagnostics_json", "type": "STRING", "links": None, "slot_index": 8},
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

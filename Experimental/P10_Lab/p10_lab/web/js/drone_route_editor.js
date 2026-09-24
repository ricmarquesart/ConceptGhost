import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_CLASS = "ConceptGhostP10DroneRouteAuthoring";
const COLORS = ["#ffb040", "#4ebeff", "#86e276", "#de76ff", "#ff6868", "#ffdc5a", "#5ee8d4"];
const MAX_ORTHO_ZOOM = 160.0;
const MAX_PERSPECTIVE_ZOOM = 48.0;
const GEOMETRY_DRAW_BUDGET = 100000;
const MESH_DRAW_BUDGET = 24000;
const PREVIEW_MODES = ["POINTS_LOW", "POINTS_MEDIUM", "POINTS_HIGH", "MESH_SURFACE", "MESH_WIREFRAME"];
const ROUTE_PRESET_SCHEMA = "ConceptGhost.P10DroneRoutePreset.v0.1";

function chainCallback(object, name, callback) {
    const original = object[name];
    object[name] = function (...args) {
        const value = original?.apply(this, args);
        callback.apply(this, args);
        return value;
    };
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function findWidget(node, name) {
    return node.widgets?.find((widget) => widget.name === name) ?? null;
}

function imageUrl(meta) {
    if (!meta?.filename) return null;
    const params = new URLSearchParams({
        filename: meta.filename,
        subfolder: meta.subfolder || "",
        type: meta.type || "output",
        rand: String(Date.now()),
    });
    return api.apiURL("/view?" + params.toString());
}

function validPlan(plan) {
    return plan && Array.isArray(plan.missions) && plan.missions.length >= 1;
}

function defaultPoint(projection) {
    const bounds = {};
    for (const panel of projection?.panels || []) {
        bounds[panel.x_axis] = panel.x_extent;
        bounds[panel.y_axis] = panel.y_extent;
    }
    const midpoint = (extent) => extent ? (Number(extent.min) + Number(extent.max)) * 0.5 : 0;
    return {
        right: midpoint(bounds.right),
        up: midpoint(bounds.up),
        forward: midpoint(bounds.forward),
    };
}

function seedPath(projection) {
    const center = defaultPoint(projection);
    let forwardExtent = null;
    for (const panel of projection?.panels || []) {
        if (panel.x_axis === "forward") forwardExtent = panel.x_extent;
        if (panel.y_axis === "forward") forwardExtent = panel.y_extent;
    }
    const span = forwardExtent ? Number(forwardExtent.max) - Number(forwardExtent.min) : 2;
    const delta = Math.max(span * 0.05, 0.25);
    return [
        { right: center.right, up: center.up, forward: center.forward - delta },
        { right: center.right, up: center.up, forward: center.forward + delta },
    ];
}

function statusForPlan(plan) {
    if (!validPlan(plan)) return { ok: false, text: "Execute o node uma vez para carregar a cena." };
    const active = plan.missions.filter((m) => m.enabled !== false);
    if (!active.length) return { ok: false, text: "Nenhum drone ativo." };
    for (const mission of active) {
        const points = Array.isArray(mission.waypoints) ? mission.waypoints : [];
        if (mission.mode === "SPIN_360" && points.length !== 1) {
            return { ok: false, text: `${mission.name}: 360° precisa de 1 ponto.` };
        }
        if (mission.mode !== "SPIN_360" && points.length < 2) {
            return { ok: false, text: `${mission.name}: PATH precisa de pelo menos 2 pontos.` };
        }
        if (mission.mode !== "SPIN_360" && mission.orientation_mode === "LOOK_AT_TARGET" && !mission.look_target) {
            return { ok: false, text: `${mission.name}: LOOK_AT_TARGET precisa de alvo.` };
        }
        if (mission.mode !== "SPIN_360" && mission.orientation_mode === "MANUAL_DIRECTION" && !mission.manual_direction) {
            return { ok: false, text: `${mission.name}: MANUAL_DIRECTION precisa de direção.` };
        }
    }
    return { ok: true, text: `${active.length} drone(s) ativo(s) · plano válido` };
}

function setupEditor(node) {
    if (node.__cgRouteEditorInstalled) return;
    node.__cgRouteEditorInstalled = true;

    const routeWidget = findWidget(node, "route_plan_json");
    if (!routeWidget) return;
    const framesWidget = findWidget(node, "frames_per_drone");
    const clearanceWidget = findWidget(node, "min_clearance_m");

    function sanitizeNumericWidgets() {
        if (framesWidget) {
            const value = Number(framesWidget.value);
            if (!Number.isFinite(value) || value < 2 || value > 240) framesWidget.value = 30;
        }
        if (clearanceWidget) {
            const raw = clearanceWidget.value;
            const value = Number(raw);
            if (raw == null || raw === "" || !Number.isFinite(value) || value < 0 || value > 10) {
                clearanceWidget.value = 0.20;
            }
        }
    }
    sanitizeNumericWidgets();

    // JSON is still serialized by the normal ComfyUI widget, but the artist
    // edits it through the tri-view UI instead of a text box.
    routeWidget.hidden = true;
    routeWidget.computeSize = () => [0, -4];

    const root = document.createElement("div");
    root.style.cssText = [
        "display:flex",
        "flex-direction:column",
        "gap:6px",
        "width:100%",
        "height:1320px",
        "box-sizing:border-box",
        "padding:6px",
        "background:#171717",
        "border:1px solid #444",
        "border-radius:6px",
        "color:#ddd",
        "font:12px sans-serif",
        "overflow:hidden",
    ].join(";");

    const toolbar = document.createElement("div");
    toolbar.style.cssText = "display:flex;flex-wrap:wrap;gap:5px;align-items:center;";

    const droneSelect = document.createElement("select");
    const modeSelect = document.createElement("select");
    const orientationSelect = document.createElement("select");
    const previewModeSelect = document.createElement("select");
    for (const [value, label] of [
        ["POINTS_LOW", "Points Low"],
        ["POINTS_MEDIUM", "Points Medium"],
        ["POINTS_HIGH", "Points High"],
        ["MESH_SURFACE", "Mesh Surface"],
        ["MESH_WIREFRAME", "Mesh Wireframe"],
    ]) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        previewModeSelect.appendChild(option);
    }
    for (const [value, label] of [
        ["LOOK_AT_TARGET", "Look at target"],
        ["LOOK_ALONG_PATH", "Look along path"],
        ["MANUAL_DIRECTION", "Manual direction"],
    ]) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        orientationSelect.appendChild(option);
    }
    for (const [value, label] of [["PATH", "Path"], ["SPIN_360", "360°"]]) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        modeSelect.appendChild(option);
    }

    const button = (label, title) => {
        const element = document.createElement("button");
        element.type = "button";
        element.textContent = label;
        element.title = title || label;
        element.style.cssText =
            "background:#2d2d2d;color:#eee;border:1px solid #555;border-radius:4px;padding:4px 8px;cursor:pointer;";
        return element;
    };

    const addDrone = button("+ Drone", "Adicionar um drone, até 7");
    const removeDrone = button("− Drone", "Remover o drone selecionado");
    const deletePoint = button("Excluir ponto", "Excluir waypoint selecionado");
    const undo = button("Desfazer", "Desfazer a última edição");
    const clearRoute = button("Limpar rota", "Limpar os pontos do drone atual");
    const resetRoute = button("Resetar rota", "Restaurar a rota-semente desta mesma cena sem apagar P9 nem a visualização");
    const frameAll = button("Enquadrar tudo", "Restaurar zoom/pan das quatro vistas sem alterar rota ou P9");
    const exportRoute = button("Exportar trajeto", "Salvar drones/rotas em um JSON portátil para reutilizar em outros testes");
    const importRoute = button("Importar trajeto", "Importar rapidamente um JSON de trajeto e rebindar à cena atual");
    const importInput = document.createElement("input");
    importInput.type = "file";
    importInput.accept = ".json,application/json";
    importInput.style.display = "none";
    const editTarget = button("Editar alvo", "Definir/arrastar o LOOK_AT_TARGET nas vistas ortográficas");
    const yawInput = document.createElement("input");
    const pitchInput = document.createElement("input");
    for (const input of [yawInput, pitchInput]) {
        input.type = "number";
        input.step = "1";
        input.style.cssText = "width:58px;background:#222;color:#eee;border:1px solid #555;border-radius:3px;padding:3px;";
    }
    yawInput.title = "Yaw manual em graus";
    pitchInput.title = "Pitch manual em graus";
    const pointSizeInput = document.createElement("input");
    pointSizeInput.type = "range";
    pointSizeInput.min = "0.5";
    pointSizeInput.max = "4.0";
    pointSizeInput.step = "0.25";
    pointSizeInput.value = "1.25";
    pointSizeInput.title = "Tamanho visual dos pontos; não altera a geometria";
    pointSizeInput.style.cssText = "width:90px;";
    const pointSizeValue = document.createElement("span");
    pointSizeValue.textContent = "1.25 px";
    pointSizeValue.style.cssText = "min-width:48px;color:#aaa;";

    toolbar.append(
        "Display:", previewModeSelect, "Point size:", pointSizeInput, pointSizeValue,
        "Drone:", droneSelect, modeSelect,
        "Aim:", orientationSelect, editTarget,
        "Yaw:", yawInput, "Pitch:", pitchInput,
        addDrone, removeDrone, deletePoint, undo, clearRoute, resetRoute, frameAll,
        exportRoute, importRoute, importInput
    );

    const help = document.createElement("div");
    help.textContent =
        "PASSO 1/2 neste workflow: após o primeiro Run, edite os drones; depois clique Run novamente para COMMITAR a rota. " +
        "PERSPECTIVE: arraste para orbitar, Shift+arraste para pan; roda ou botões −/+ = zoom profundo. " +
        "TOP/SIDE/FRONT: roda ou botões −/+ = zoom profundo; Shift+arraste ou botão do meio = pan mantendo o eixo travado. " +
        "Adicionar/mover pontos preserva exatamente zoom e pan. Exportar/Importar trajeto reutiliza os drones em novos testes. " +
        "LOOK_AT_TARGET usa Editar alvo. Display alterna Points/visual Mesh LOD sem mudar a autoridade P9; Point size é apenas visual. " +
        "Resetar rota não apaga a cena; Enquadrar tudo só restaura a câmera das vistas.";
    help.style.cssText = "color:#aaa;line-height:1.3;";

    const cameraPreviewWrap = document.createElement("div");
    cameraPreviewWrap.style.cssText =
        "display:flex;flex-direction:column;gap:3px;background:#111;border:1px solid #333;border-radius:4px;padding:5px;";
    const cameraPreviewTitle = document.createElement("div");
    cameraPreviewTitle.textContent = "Selected Camera View · selecione P1/P2/P3…";
    cameraPreviewTitle.style.cssText = "color:#ddd;font-weight:600;";
    const cameraPreviewCanvas = document.createElement("canvas");
    cameraPreviewCanvas.width = 640;
    cameraPreviewCanvas.height = 360;
    cameraPreviewCanvas.style.cssText =
        "display:block;width:min(100%,640px);height:auto;align-self:center;background:#0b0b0b;border:1px solid #2e2e2e;";
    const cameraPreviewHint = document.createElement("div");
    cameraPreviewHint.textContent =
        "Live preview rápido do P9. Para checagem de maior confiança, use P10 · Selected Drone Camera Preview.";
    cameraPreviewHint.style.cssText = "color:#888;font-size:10px;";
    cameraPreviewWrap.append(cameraPreviewTitle, cameraPreviewCanvas, cameraPreviewHint);

    const canvasWrap = document.createElement("div");
    canvasWrap.style.cssText =
        "position:relative;flex:1;min-height:0;overflow:auto;background:#111;border:1px solid #333;border-radius:4px;";

    const canvas = document.createElement("canvas");
    canvas.style.cssText = "display:block;width:100%;height:auto;cursor:crosshair;user-select:none;touch-action:none;";
    canvasWrap.appendChild(canvas);

    const footer = document.createElement("div");
    footer.style.cssText = "display:flex;justify-content:space-between;gap:8px;color:#aaa;";
    const status = document.createElement("span");
    const selected = document.createElement("span");
    footer.append(status, selected);

    root.append(toolbar, help, cameraPreviewWrap, canvasWrap, footer);

    node.addDOMWidget("cg_drone_route_editor", "route_editor", root, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 1120,
        getHeight: () => 1320,
    });

    node.setSize?.([Math.max(node.size?.[0] || 900, 1180), Math.max(node.size?.[1] || 900, 1490)]);

    const ctx = canvas.getContext("2d");
    const cameraCtx = cameraPreviewCanvas.getContext("2d");
    const state = {
        plan: null,
        projection: null,
        activeMission: 0,
        selectedPoint: null,
        dragging: false,
        dragHistoryPushed: false,
        history: [],
        metadata: null,
        collisionStale: false,
        sceneKey: null,
        initialSeedPlan: null,
        orbitYaw: -35 * Math.PI / 180,
        orbitPitch: -18 * Math.PI / 180,
        orbitZoom: 1.0,
        orbitPanX: 0,
        orbitPanY: 0,
        orbitDragging: false,
        orbitPanning: false,
        orbitLast: null,
        orthoViews: {},
        orthoPanning: false,
        orthoPanPanel: null,
        orthoLast: null,
        editingTarget: false,
        targetDragging: false,
        previewMode: "POINTS_MEDIUM",
        pointSize: 1.25,
    };

    function pushHistory() {
        if (!validPlan(state.plan)) return;
        state.history.push(clone(state.plan));
        if (state.history.length > 40) state.history.shift();
    }

    function persist() {
        if (!validPlan(state.plan)) return;
        sanitizeNumericWidgets();
        state.plan.route_authority = "ARTIST_AUTHORED";
        delete state.plan.route_plan_sha256;
        state.plan.route_plan_dirty = true;
        routeWidget.value = JSON.stringify(state.plan, null, 2);
        routeWidget.callback?.(routeWidget.value);
        state.collisionStale = true;
        // Viewport is artist state. Route edits must not auto-fit or zoom out.
        // Only initial scene framing, explicit import, or "Enquadrar tudo" may reframe.
        node.graph?.setDirtyCanvas?.(true, true);
        updateToolbar();
        draw();
    }

    function setPlan(plan, persistValue = true) {
        if (!validPlan(plan)) return;
        state.plan = clone(plan);
        state.activeMission = Math.min(state.activeMission, state.plan.missions.length - 1);
        state.selectedPoint = null;
        if (persistValue) {
            routeWidget.value = JSON.stringify(state.plan, null, 2);
            routeWidget.callback?.(routeWidget.value);
        }
        updateToolbar();
        draw();
    }

    function activeMission() {
        return state.plan?.missions?.[state.activeMission] ?? null;
    }


    function normalizeVector(vector) {
        const length = Math.hypot(Number(vector.right) || 0, Number(vector.up) || 0, Number(vector.forward) || 0);
        if (length < 1e-9) return { right: 0, up: 0, forward: 1 };
        return {
            right: (Number(vector.right) || 0) / length,
            up: (Number(vector.up) || 0) / length,
            forward: (Number(vector.forward) || 0) / length,
        };
    }

    function lookVectorForMission(mission, pointIndex) {
        const points = mission?.waypoints || [];
        const point = points[pointIndex];
        if (!point) return { right: 0, up: 0, forward: 1 };
        if (mission.mode === "SPIN_360") return { right: 0, up: 0, forward: 1 };

        const orientation = mission.orientation_mode || "LOOK_ALONG_PATH";
        if (orientation === "LOOK_AT_TARGET" && mission.look_target) {
            return normalizeVector({
                right: Number(mission.look_target.right) - Number(point.right),
                up: Number(mission.look_target.up) - Number(point.up),
                forward: Number(mission.look_target.forward) - Number(point.forward),
            });
        }
        if (orientation === "MANUAL_DIRECTION" && mission.manual_direction) {
            return normalizeVector(mission.manual_direction);
        }

        const neighbor = points[Math.min(pointIndex + 1, points.length - 1)] ||
            points[Math.max(0, pointIndex - 1)] || point;
        let vector = {
            right: Number(neighbor.right) - Number(point.right),
            up: Number(neighbor.up) - Number(point.up),
            forward: Number(neighbor.forward) - Number(point.forward),
        };
        if (Math.hypot(vector.right, vector.up, vector.forward) < 1e-9 && pointIndex > 0) {
            const prior = points[pointIndex - 1];
            vector = {
                right: Number(point.right) - Number(prior.right),
                up: Number(point.up) - Number(prior.up),
                forward: Number(point.forward) - Number(prior.forward),
            };
        }
        return normalizeVector(vector);
    }

    function vectorDot(a, b) {
        return Number(a.right) * Number(b.right) +
            Number(a.up) * Number(b.up) +
            Number(a.forward) * Number(b.forward);
    }

    function physicalCrossRuf(a, b) {
        return {
            right: -(Number(a.up) * Number(b.forward) - Number(a.forward) * Number(b.up)),
            up: -(Number(a.forward) * Number(b.right) - Number(a.right) * Number(b.forward)),
            forward: -(Number(a.right) * Number(b.up) - Number(a.up) * Number(b.right)),
        };
    }

    function cameraBasisForLook(rawLook) {
        const forward = normalizeVector(rawLook);
        const canonicalUp = { right: 0, up: 1, forward: 0 };
        let right = physicalCrossRuf(forward, canonicalUp);
        if (Math.hypot(right.right, right.up, right.forward) < 1e-8) {
            const canonicalRight = { right: 1, up: 0, forward: 0 };
            const amount = vectorDot(canonicalRight, forward);
            right = {
                right: canonicalRight.right - amount * forward.right,
                up: canonicalRight.up - amount * forward.up,
                forward: canonicalRight.forward - amount * forward.forward,
            };
        }
        right = normalizeVector(right);
        const up = normalizeVector(physicalCrossRuf(right, forward));
        return { right, up, forward };
    }

    function cameraContract() {
        return state.metadata?.camera_preview_contract || null;
    }

    function selectedCameraState() {
        const mission = activeMission();
        const pointIndex = state.selectedPoint;
        const point = pointIndex == null ? null : mission?.waypoints?.[pointIndex];
        if (!mission || !point) return null;
        const look = lookVectorForMission(mission, pointIndex);
        return {
            mission,
            pointIndex,
            point,
            look,
            basis: cameraBasisForLook(look),
        };
    }

    function manualDirectionFromInputs() {
        const yaw = (Number(yawInput.value) || 0) * Math.PI / 180;
        const pitch = (Number(pitchInput.value) || 0) * Math.PI / 180;
        const cp = Math.cos(pitch);
        return normalizeVector({
            right: Math.sin(yaw) * cp,
            up: Math.sin(pitch),
            forward: Math.cos(yaw) * cp,
        });
    }

    function updateManualInputs(mission) {
        const direction = normalizeVector(mission?.manual_direction || { right: 0, up: 0, forward: 1 });
        const yaw = Math.atan2(direction.right, direction.forward) * 180 / Math.PI;
        const horizontal = Math.hypot(direction.right, direction.forward);
        const pitch = Math.atan2(direction.up, horizontal) * 180 / Math.PI;
        yawInput.value = yaw.toFixed(1);
        pitchInput.value = pitch.toFixed(1);
    }

    function updateToolbar() {
        droneSelect.innerHTML = "";
        const missions = state.plan?.missions || [];
        missions.forEach((mission, index) => {
            const option = document.createElement("option");
            option.value = String(index);
            option.textContent = mission.name || `drone_${index + 1}`;
            option.selected = index === state.activeMission;
            droneSelect.appendChild(option);
        });
        const mission = activeMission();
        modeSelect.value = mission?.mode || "PATH";
        orientationSelect.value = mission?.orientation_mode || "LOOK_ALONG_PATH";
        orientationSelect.disabled = mission?.mode === "SPIN_360";
        editTarget.disabled = mission?.mode === "SPIN_360" || orientationSelect.value !== "LOOK_AT_TARGET";
        editTarget.style.background = state.editingTarget ? "#594d13" : "#2d2d2d";
        yawInput.disabled = mission?.mode === "SPIN_360" || orientationSelect.value !== "MANUAL_DIRECTION";
        pitchInput.disabled = yawInput.disabled;
        updateManualInputs(mission);
        const meshAvailable = Boolean(state.metadata?.preview_geometry?.mesh_lod?.available);
        for (const option of previewModeSelect.options) {
            if (String(option.value).startsWith("MESH_")) option.disabled = !meshAvailable;
        }
        if (String(state.previewMode).startsWith("MESH_") && !meshAvailable) state.previewMode = "POINTS_MEDIUM";
        previewModeSelect.value = state.previewMode;
        pointSizeInput.disabled = String(state.previewMode).startsWith("MESH_");
        pointSizeInput.value = String(state.pointSize);
        pointSizeValue.textContent = Number(state.pointSize).toFixed(2) + " px";
        addDrone.disabled = missions.length >= 7;
        removeDrone.disabled = missions.length <= 1;
        deletePoint.disabled = state.selectedPoint == null;
        undo.disabled = state.history.length === 0;

        const planStatus = statusForPlan(state.plan);
        const collision = state.metadata?.collision_preflight;
        if (!planStatus.ok) {
            status.textContent = planStatus.text;
            status.style.color = "#ffb040";
        } else if (state.collisionStale) {
            status.textContent = planStatus.text + " · rota editada · execute Queue Prompt para aplicar/revalidar";
            status.style.color = "#ffdc5a";
        } else if (collision?.blocked_mission_count > 0) {
            status.textContent =
                planStatus.text + ` · ${collision.blocked_segment_count} trecho(s) bloqueado(s)`;
            status.style.color = "#ff6868";
        } else if (collision) {
            status.textContent = planStatus.text + " · clearance OK";
            status.style.color = "#86e276";
        } else {
            status.textContent = planStatus.text;
            status.style.color = "#86e276";
        }
        selected.textContent =
            state.selectedPoint == null
                ? (state.editingTarget ? "Editando alvo da câmera" : "Nenhum ponto selecionado")
                : `Ponto ${state.selectedPoint + 1}`;
    }

    function panelAt(x, y) {
        return (state.projection?.panels || []).find((panel) => {
            const r = panel.plot_rect_px;
            return x >= r.x && x <= r.x + r.width && y >= r.y && y <= r.y + r.height;
        }) || null;
    }

    function baseOrthoView(panel) {
        const xMin = Number(panel.x_extent.min);
        const xMax = Number(panel.x_extent.max);
        const yMin = Number(panel.y_extent.min);
        const yMax = Number(panel.y_extent.max);
        return {
            baseCenterX: (xMin + xMax) * 0.5,
            baseCenterY: (yMin + yMax) * 0.5,
            baseSpanX: Math.max(xMax - xMin, 1e-9),
            baseSpanY: Math.max(yMax - yMin, 1e-9),
            zoom: 1.0,
            panX: 0.0,
            panY: 0.0,
        };
    }

    function ensureOrthoViews(reset = false) {
        for (const panel of state.projection?.panels || []) {
            if (reset || !state.orthoViews[panel.name]) {
                state.orthoViews[panel.name] = baseOrthoView(panel);
            }
        }
    }

    function orthoExtent(panel) {
        ensureOrthoViews(false);
        const view = state.orthoViews[panel.name] || baseOrthoView(panel);
        const zoom = Math.max(0.15, Math.min(MAX_ORTHO_ZOOM, Number(view.zoom) || 1));
        const spanX = view.baseSpanX / zoom;
        const spanY = view.baseSpanY / zoom;
        const centerX = view.baseCenterX + Number(view.panX || 0);
        const centerY = view.baseCenterY + Number(view.panY || 0);
        return {
            minX: centerX - spanX * 0.5,
            maxX: centerX + spanX * 0.5,
            minY: centerY - spanY * 0.5,
            maxY: centerY + spanY * 0.5,
            spanX,
            spanY,
            centerX,
            centerY,
            view,
        };
    }

    function project(panel, point) {
        const r = panel.plot_rect_px;
        const extent = orthoExtent(panel);
        const xValue = Number(point[panel.x_axis]);
        const yValue = Number(point[panel.y_axis]);
        const xAmount = (xValue - extent.minX) / extent.spanX;
        const yAmount = (yValue - extent.minY) / extent.spanY;
        return {
            x: r.x + xAmount * r.width,
            y: r.y + (1 - yAmount) * r.height,
        };
    }

    function worldFromPanel(panel, x, y, base) {
        const r = panel.plot_rect_px;
        const extent = orthoExtent(panel);
        const xAmount = Math.max(0, Math.min(1, (x - r.x) / r.width));
        const yAmount = Math.max(0, Math.min(1, 1 - (y - r.y) / r.height));
        const point = { ...base };
        point[panel.x_axis] = extent.minX + xAmount * extent.spanX;
        point[panel.y_axis] = extent.minY + yAmount * extent.spanY;
        return point;
    }

    function routePointsForVisibility() {
        const points = [];
        for (const mission of state.plan?.missions || []) {
            if (mission.enabled === false) continue;
            for (const point of mission.waypoints || []) points.push(point);
            if (mission.orientation_mode === "LOOK_AT_TARGET" && mission.look_target) points.push(mission.look_target);
        }
        return points;
    }

    function ensureRouteVisible() {
        if (!state.projection || !validPlan(state.plan)) return;
        ensureOrthoViews(false);
        const points = routePointsForVisibility();
        if (!points.length) return;
        for (const panel of state.projection.panels || []) {
            const extent = orthoExtent(panel);
            const xs = points.map((p) => Number(p[panel.x_axis])).filter(Number.isFinite);
            const ys = points.map((p) => Number(p[panel.y_axis])).filter(Number.isFinite);
            if (!xs.length || !ys.length) continue;
            const marginX = extent.spanX * 0.06;
            const marginY = extent.spanY * 0.06;
            const minX = Math.min(...xs) - marginX;
            const maxX = Math.max(...xs) + marginX;
            const minY = Math.min(...ys) - marginY;
            const maxY = Math.max(...ys) + marginY;
            const inside = minX >= extent.minX && maxX <= extent.maxX &&
                minY >= extent.minY && maxY <= extent.maxY;
            if (inside) continue;

            const unionMinX = Math.min(extent.minX, minX);
            const unionMaxX = Math.max(extent.maxX, maxX);
            const unionMinY = Math.min(extent.minY, minY);
            const unionMaxY = Math.max(extent.maxY, maxY);
            const desiredSpanX = unionMaxX - unionMinX;
            const desiredSpanY = unionMaxY - unionMinY;
            const scale = Math.max(desiredSpanX / extent.spanX, desiredSpanY / extent.spanY, 1.0);
            const view = extent.view;
            view.zoom = Math.max(0.15, view.zoom / scale);
            view.panX = ((unionMinX + unionMaxX) * 0.5) - view.baseCenterX;
            view.panY = ((unionMinY + unionMaxY) * 0.5) - view.baseCenterY;
        }
    }

    function perspectivePanel() {
        return state.projection?.perspective_panel || null;
    }

    function insideRect(rect, x, y) {
        return Boolean(rect) &&
            x >= rect.x && x <= rect.x + rect.width &&
            y >= rect.y && y <= rect.y + rect.height;
    }

    function zoomControlRects(panel) {
        const plot = panel?.plot_rect_px;
        if (!plot) return [];
        const size = 24;
        const gap = 4;
        const y = plot.y + 8;
        const plus = {
            action: "in",
            x: plot.x + plot.width - size - 8,
            y,
            width: size,
            height: size,
        };
        const minus = {
            action: "out",
            x: plus.x - gap - size,
            y,
            width: size,
            height: size,
        };
        return [minus, plus];
    }

    function hitZoomControl(x, y) {
        const candidates = [
            ...(perspectivePanel() ? [perspectivePanel()] : []),
            ...(state.projection?.panels || []),
        ];
        for (const panel of candidates) {
            for (const rect of zoomControlRects(panel)) {
                if (insideRect(rect, x, y)) return { panel, action: rect.action };
            }
        }
        return null;
    }

    function applyPanelZoom(panel, factor, anchorPoint = null) {
        if (!panel || !Number.isFinite(factor) || factor <= 0) return false;
        const perspective = perspectivePanel();
        if (perspective && panel === perspective) {
            state.orbitZoom = Math.max(0.20, Math.min(MAX_PERSPECTIVE_ZOOM, state.orbitZoom * factor));
            draw();
            return true;
        }

        const ortho = (state.projection?.panels || []).find((item) => item === panel || item.name === panel.name);
        if (!ortho) return false;

        const extent = orthoExtent(ortho);
        let before = null;
        if (anchorPoint) before = worldFromPanel(ortho, anchorPoint.x, anchorPoint.y, {});
        extent.view.zoom = Math.max(0.20, Math.min(MAX_ORTHO_ZOOM, extent.view.zoom * factor));
        if (before && anchorPoint) {
            const after = worldFromPanel(ortho, anchorPoint.x, anchorPoint.y, {});
            extent.view.panX += Number(before[ortho.x_axis]) - Number(after[ortho.x_axis]);
            extent.view.panY += Number(before[ortho.y_axis]) - Number(after[ortho.y_axis]);
        }
        draw();
        return true;
    }

    function zoomAtCanvasPoint(xy, factor) {
        if (!xy || !state.projection) return false;
        const perspective = perspectivePanel();
        if (perspective && insideRect(perspective.plot_rect_px, xy.x, xy.y)) {
            return applyPanelZoom(perspective, factor, xy);
        }
        const panel = panelAt(xy.x, xy.y);
        if (!panel) return false;
        return applyPanelZoom(panel, factor, xy);
    }

    function drawZoomControls(panel) {
        const rects = zoomControlRects(panel);
        if (!rects.length) return;
        ctx.save();
        for (const rect of rects) {
            ctx.fillStyle = "rgba(35,35,35,0.92)";
            ctx.strokeStyle = "#777";
            ctx.lineWidth = 1;
            ctx.fillRect(rect.x, rect.y, rect.width, rect.height);
            ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);
            ctx.fillStyle = "#f0f0f0";
            ctx.font = "bold 16px sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(rect.action === "in" ? "+" : "−", rect.x + rect.width * 0.5, rect.y + rect.height * 0.5 + 0.5);
        }
        ctx.restore();
    }

    function projectPerspective(point) {
        const panel = perspectivePanel();
        const geometry = state.metadata?.preview_geometry;
        if (!panel || !geometry) return null;
        const plot = panel.plot_rect_px;
        const center = geometry.center || [0, 0, 0];
        const radius = Math.max(Number(geometry.radius) || 1, 1e-3);
        const x = Number(point.right ?? point[0]) - Number(center[0]);
        const y = Number(point.up ?? point[1]) - Number(center[1]);
        const z = Number(point.forward ?? point[2]) - Number(center[2]);

        const cy = Math.cos(state.orbitYaw);
        const sy = Math.sin(state.orbitYaw);
        const cp = Math.cos(state.orbitPitch);
        const sp = Math.sin(state.orbitPitch);

        const x1 = cy * x - sy * z;
        const z1 = sy * x + cy * z;
        const y2 = cp * y - sp * z1;
        const z2 = sp * y + cp * z1;

        const distance = radius * 2.8 / Math.max(0.2, state.orbitZoom);
        const depth = distance - z2;
        if (depth <= radius * 0.02) return null;
        const focal = Math.min(plot.width, plot.height) * 1.05;
        return {
            x: plot.x + plot.width * 0.5 + state.orbitPanX + (x1 / depth) * focal,
            y: plot.y + plot.height * 0.5 + state.orbitPanY - (y2 / depth) * focal,
            depth,
        };
    }

    function drawArrowHead(a, b, color, scale = 1) {
        if (!a || !b) return;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const length = Math.hypot(dx, dy);
        if (length < 8) return;
        const ux = dx / length;
        const uy = dy / length;
        const px = -uy;
        const py = ux;
        const tipX = a.x + dx * 0.72;
        const tipY = a.y + dy * 0.72;
        const back = 7 * scale;
        const side = 4 * scale;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(tipX, tipY);
        ctx.lineTo(tipX - ux * back + px * side, tipY - uy * back + py * side);
        ctx.lineTo(tipX - ux * back - px * side, tipY - uy * back - py * side);
        ctx.closePath();
        ctx.fill();
    }


    function orientationTip(point, mission, pointIndex, scale) {
        const look = lookVectorForMission(mission, pointIndex);
        return {
            right: Number(point.right) + look.right * scale,
            up: Number(point.up) + look.up * scale,
            forward: Number(point.forward) + look.forward * scale,
        };
    }

    function drawTargetMarker(projectFn, target, color) {
        if (!target) return;
        const p = projectFn(target);
        if (!p) return;
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(p.x - 7, p.y);
        ctx.lineTo(p.x + 7, p.y);
        ctx.moveTo(p.x, p.y - 7);
        ctx.lineTo(p.x, p.y + 7);
        ctx.stroke();
        ctx.strokeRect(p.x - 4, p.y - 4, 8, 8);
    }

    function projectSelectedCamera(raw) {
        const selectedCamera = selectedCameraState();
        const contract = cameraContract();
        if (!selectedCamera || !contract) return null;
        const point = selectedCamera.point;
        const basis = selectedCamera.basis;
        const delta = {
            right: Number(raw.right ?? raw[0]) - Number(point.right),
            up: Number(raw.up ?? raw[1]) - Number(point.up),
            forward: Number(raw.forward ?? raw[2]) - Number(point.forward),
        };
        const depth = vectorDot(delta, basis.forward);
        if (!Number.isFinite(depth) || depth <= 1e-4) return null;
        const cameraX = vectorDot(delta, basis.right);
        const cameraY = vectorDot(delta, basis.up);
        const width = cameraPreviewCanvas.width;
        const height = cameraPreviewCanvas.height;
        const hfov = Number(contract.horizontal_fov_deg) * Math.PI / 180;
        const vfov = Number(contract.vertical_fov_deg) * Math.PI / 180;
        if (!(hfov > 0) || !(vfov > 0)) return null;
        const fx = (width * 0.5) / Math.tan(hfov * 0.5);
        const fy = (height * 0.5) / Math.tan(vfov * 0.5);
        return {
            x: width * 0.5 + cameraX / depth * fx,
            y: height * 0.5 - cameraY / depth * fy,
            depth,
        };
    }

    function selectedFrustumCorners(mission, pointIndex) {
        const point = mission?.waypoints?.[pointIndex];
        const contract = cameraContract();
        const geometry = state.metadata?.preview_geometry;
        if (!point || !contract || !geometry) return null;
        const look = lookVectorForMission(mission, pointIndex);
        const basis = cameraBasisForLook(look);
        const distance = Math.max(Number(geometry.radius || 1) * 0.09, 0.25);
        const halfWidth = Math.tan(Number(contract.horizontal_fov_deg) * Math.PI / 360) * distance;
        const halfHeight = Math.tan(Number(contract.vertical_fov_deg) * Math.PI / 360) * distance;
        const add = (sr, su) => ({
            right: Number(point.right) + basis.forward.right * distance + basis.right.right * halfWidth * sr + basis.up.right * halfHeight * su,
            up: Number(point.up) + basis.forward.up * distance + basis.right.up * halfWidth * sr + basis.up.up * halfHeight * su,
            forward: Number(point.forward) + basis.forward.forward * distance + basis.right.forward * halfWidth * sr + basis.up.forward * halfHeight * su,
        });
        return {
            apex: point,
            corners: [add(-1,-1), add(1,-1), add(1,1), add(-1,1)],
        };
    }

    function drawSelectedFrustum(projectFn, mission, pointIndex, color) {
        if (pointIndex == null) return;
        const frustum = selectedFrustumCorners(mission, pointIndex);
        if (!frustum) return;
        const apex = projectFn(frustum.apex);
        const corners = frustum.corners.map(projectFn);
        if (!apex || corners.some((item) => !item)) return;
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.3;
        ctx.setLineDash([5,3]);
        for (const corner of corners) {
            ctx.beginPath();
            ctx.moveTo(apex.x,apex.y);
            ctx.lineTo(corner.x,corner.y);
            ctx.stroke();
        }
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(corners[0].x,corners[0].y);
        for (let i=1;i<corners.length;i++) ctx.lineTo(corners[i].x,corners[i].y);
        ctx.closePath();
        ctx.stroke();
        ctx.restore();
    }

    function drawSelectedCameraView() {
        const width = cameraPreviewCanvas.width;
        const height = cameraPreviewCanvas.height;
        cameraCtx.clearRect(0,0,width,height);
        cameraCtx.fillStyle = "#0b0b0b";
        cameraCtx.fillRect(0,0,width,height);
        const selectedCamera = selectedCameraState();
        const geometry = state.metadata?.preview_geometry;
        if (!selectedCamera || !geometry) {
            cameraCtx.fillStyle = "#777";
            cameraCtx.font = "14px sans-serif";
            cameraCtx.textAlign = "center";
            cameraCtx.fillText("Selecione um waypoint para ver exatamente para onde a câmera aponta.",width*0.5,height*0.5);
            cameraPreviewTitle.textContent = "Selected Camera View · nenhum waypoint selecionado";
            return;
        }
        const mission = selectedCamera.mission;
        cameraPreviewTitle.textContent = "Selected Camera View · " + mission.name + " · P" + (selectedCamera.pointIndex + 1);

        if (String(state.previewMode).startsWith("MESH_") && activeMeshLod()) {
            const mesh = activeMeshLod();
            const vertices = mesh.vertices || [];
            const faces = mesh.faces || [];
            const triangles = [];
            const stride = Math.max(1, Math.ceil(faces.length / MESH_DRAW_BUDGET));
            for (let index=0; index<faces.length; index+=stride) {
                const face=faces[index];
                const a=projectSelectedCamera(vertices[face[0]]);
                const b=projectSelectedCamera(vertices[face[1]]);
                const c=projectSelectedCamera(vertices[face[2]]);
                if(!a||!b||!c) continue;
                const minX=Math.min(a.x,b.x,c.x), maxX=Math.max(a.x,b.x,c.x);
                const minY=Math.min(a.y,b.y,c.y), maxY=Math.max(a.y,b.y,c.y);
                if(maxX<0||minX>width||maxY<0||minY>height) continue;
                triangles.push({a,b,c,depth:(a.depth+b.depth+c.depth)/3,color:averageTriangleColor(vertices,face)});
            }
            if(state.previewMode==="MESH_SURFACE") triangles.sort((left,right)=>right.depth-left.depth);
            for(const tri of triangles){
                cameraCtx.beginPath();
                cameraCtx.moveTo(tri.a.x,tri.a.y);
                cameraCtx.lineTo(tri.b.x,tri.b.y);
                cameraCtx.lineTo(tri.c.x,tri.c.y);
                cameraCtx.closePath();
                if(state.previewMode==="MESH_SURFACE"){
                    cameraCtx.fillStyle="rgba("+tri.color[0]+","+tri.color[1]+","+tri.color[2]+",0.48)";
                    cameraCtx.fill();
                    cameraCtx.strokeStyle="rgba(20,20,20,0.18)";
                    cameraCtx.lineWidth=0.5;
                    cameraCtx.stroke();
                } else {
                    cameraCtx.strokeStyle="rgba(215,225,235,0.62)";
                    cameraCtx.lineWidth=0.7;
                    cameraCtx.stroke();
                }
            }
        } else {
            const points=activePointLod().points || [];
            const stride=Math.max(1,Math.ceil(points.length/GEOMETRY_DRAW_BUDGET));
            const size=Math.max(0.5,Math.min(4.0,Number(state.pointSize)||1.25));
            for(let index=0;index<points.length;index+=stride){
                const raw=points[index];
                const p=projectSelectedCamera(raw);
                if(!p||p.x<0||p.x>width||p.y<0||p.y>height) continue;
                cameraCtx.fillStyle="rgba("+(raw[3] ?? 150)+","+(raw[4] ?? 150)+","+(raw[5] ?? 150)+",0.82)";
                cameraCtx.fillRect(p.x-size*0.5,p.y-size*0.5,size,size);
            }
        }

        cameraCtx.strokeStyle="rgba(255,255,255,0.55)";
        cameraCtx.lineWidth=1;
        cameraCtx.beginPath();
        cameraCtx.moveTo(width*0.5-8,height*0.5);
        cameraCtx.lineTo(width*0.5+8,height*0.5);
        cameraCtx.moveTo(width*0.5,height*0.5-8);
        cameraCtx.lineTo(width*0.5,height*0.5+8);
        cameraCtx.stroke();
        cameraCtx.fillStyle="#aaa";
        cameraCtx.font="11px sans-serif";
        cameraCtx.textAlign="left";
        cameraCtx.fillText(state.previewMode+" · live P9 preview",8,height-9);
    }

    function activePointLod() {
        const geometry = state.metadata?.preview_geometry;
        if (!geometry) return { points: [] };
        const lod = geometry.point_lods?.[state.previewMode];
        if (lod?.points) return lod;
        return geometry.point_lods?.POINTS_MEDIUM || { points: geometry.points || [] };
    }

    function activeMeshLod() {
        const mesh = state.metadata?.preview_geometry?.mesh_lod;
        return mesh?.available ? mesh : null;
    }

    function averageTriangleColor(vertices, face) {
        const a = vertices[face[0]] || [];
        const b = vertices[face[1]] || [];
        const c = vertices[face[2]] || [];
        return [
            Math.round(((Number(a[3]) || 150) + (Number(b[3]) || 150) + (Number(c[3]) || 150)) / 3),
            Math.round(((Number(a[4]) || 150) + (Number(b[4]) || 150) + (Number(c[4]) || 150)) / 3),
            Math.round(((Number(a[5]) || 150) + (Number(b[5]) || 150) + (Number(c[5]) || 150)) / 3),
        ];
    }

    function drawPerspectiveMesh(mode) {
        const panel = perspectivePanel();
        const mesh = activeMeshLod();
        if (!panel || !mesh) return false;
        const plot = panel.plot_rect_px;
        const vertices = mesh.vertices || [];
        const faces = mesh.faces || [];
        const stride = Math.max(1, Math.ceil(faces.length / MESH_DRAW_BUDGET));
        const triangles = [];
        for (let index = 0; index < faces.length; index += stride) {
            const face = faces[index];
            const a = projectPerspective(vertices[face[0]]);
            const b = projectPerspective(vertices[face[1]]);
            const c = projectPerspective(vertices[face[2]]);
            if (!a || !b || !c) continue;
            const minX = Math.min(a.x,b.x,c.x), maxX = Math.max(a.x,b.x,c.x);
            const minY = Math.min(a.y,b.y,c.y), maxY = Math.max(a.y,b.y,c.y);
            if (maxX < plot.x || minX > plot.x + plot.width || maxY < plot.y || minY > plot.y + plot.height) continue;
            triangles.push({a,b,c,depth:(a.depth+b.depth+c.depth)/3,color:averageTriangleColor(vertices,face)});
        }
        if (mode === "MESH_SURFACE") triangles.sort((left,right) => right.depth-left.depth);
        ctx.save();
        ctx.beginPath();
        ctx.rect(plot.x,plot.y,plot.width,plot.height);
        ctx.clip();
        for (const tri of triangles) {
            ctx.beginPath();
            ctx.moveTo(tri.a.x,tri.a.y);
            ctx.lineTo(tri.b.x,tri.b.y);
            ctx.lineTo(tri.c.x,tri.c.y);
            ctx.closePath();
            if (mode === "MESH_SURFACE") {
                ctx.fillStyle = "rgba(" + tri.color[0] + "," + tri.color[1] + "," + tri.color[2] + ",0.42)";
                ctx.fill();
                ctx.strokeStyle = "rgba(15,15,15,0.16)";
                ctx.lineWidth = 0.5;
                ctx.stroke();
            } else {
                ctx.strokeStyle = "rgba(205,215,225,0.56)";
                ctx.lineWidth = 0.65;
                ctx.stroke();
            }
        }
        ctx.restore();
        return true;
    }

    function drawOrthographicMesh(panel, mode) {
        const mesh = activeMeshLod();
        if (!mesh) return false;
        const plot = panel.plot_rect_px;
        const vertices = mesh.vertices || [];
        const faces = mesh.faces || [];
        const stride = Math.max(1, Math.ceil(faces.length / MESH_DRAW_BUDGET));
        const hiddenAxis = ["right","up","forward"].find((axis) => axis !== panel.x_axis && axis !== panel.y_axis) || "forward";
        const axisIndex = { right:0, up:1, forward:2 }[hiddenAxis];
        const triangles = [];
        for (let index = 0; index < faces.length; index += stride) {
            const face = faces[index];
            const va = vertices[face[0]], vb = vertices[face[1]], vc = vertices[face[2]];
            if (!va || !vb || !vc) continue;
            const a = project(panel, geometryPoint(va));
            const b = project(panel, geometryPoint(vb));
            const c = project(panel, geometryPoint(vc));
            const minX = Math.min(a.x,b.x,c.x), maxX = Math.max(a.x,b.x,c.x);
            const minY = Math.min(a.y,b.y,c.y), maxY = Math.max(a.y,b.y,c.y);
            if (maxX < plot.x || minX > plot.x + plot.width || maxY < plot.y || minY > plot.y + plot.height) continue;
            triangles.push({a,b,c,depth:(Number(va[axisIndex])+Number(vb[axisIndex])+Number(vc[axisIndex]))/3,color:averageTriangleColor(vertices,face)});
        }
        if (mode === "MESH_SURFACE") triangles.sort((left,right) => left.depth-right.depth);
        ctx.save();
        ctx.beginPath();
        ctx.rect(plot.x,plot.y,plot.width,plot.height);
        ctx.clip();
        for (const tri of triangles) {
            ctx.beginPath();
            ctx.moveTo(tri.a.x,tri.a.y);
            ctx.lineTo(tri.b.x,tri.b.y);
            ctx.lineTo(tri.c.x,tri.c.y);
            ctx.closePath();
            if (mode === "MESH_SURFACE") {
                ctx.fillStyle = "rgba(" + tri.color[0] + "," + tri.color[1] + "," + tri.color[2] + ",0.42)";
                ctx.fill();
                ctx.strokeStyle = "rgba(15,15,15,0.14)";
                ctx.lineWidth = 0.5;
                ctx.stroke();
            } else {
                ctx.strokeStyle = "rgba(205,215,225,0.56)";
                ctx.lineWidth = 0.65;
                ctx.stroke();
            }
        }
        ctx.restore();
        return true;
    }

    function drawPerspectiveScene() {
        const panel = perspectivePanel();
        const geometry = state.metadata?.preview_geometry;
        if (!panel || !geometry?.points) return;
        const plot = panel.plot_rect_px;

        ctx.save();
        ctx.beginPath();
        ctx.rect(plot.x, plot.y, plot.width, plot.height);
        ctx.clip();

        if (String(state.previewMode).startsWith("MESH_")) {
            ctx.restore();
            drawPerspectiveMesh(state.previewMode);
            ctx.save();
            ctx.beginPath();
            ctx.rect(plot.x, plot.y, plot.width, plot.height);
            ctx.clip();
        } else {
            const points = activePointLod().points || [];
            const drawStride = Math.max(1, Math.ceil(points.length / GEOMETRY_DRAW_BUDGET));
            const size = Math.max(0.5, Math.min(4.0, Number(state.pointSize) || 1.25));
            for (let index = 0; index < points.length; index += drawStride) {
                const raw = points[index];
                const p = projectPerspective(raw);
                if (!p) continue;
                if (p.x < plot.x || p.x > plot.x + plot.width || p.y < plot.y || p.y > plot.y + plot.height) continue;
                ctx.fillStyle = `rgba(${raw[3] ?? 150},${raw[4] ?? 150},${raw[5] ?? 150},0.72)`;
                ctx.fillRect(p.x - size * 0.5, p.y - size * 0.5, size, size);
            }
        }

        for (let missionIndex = 0; missionIndex < (state.plan?.missions || []).length; missionIndex++) {
            const mission = state.plan.missions[missionIndex];
            if (mission.enabled === false) continue;
            const color = COLORS[missionIndex % COLORS.length];
            const projected = (mission.waypoints || []).map(projectPerspective).filter(Boolean);
            if (mission.mode === "PATH" && projected.length > 1) {
                ctx.strokeStyle = color;
                ctx.lineWidth = missionIndex === state.activeMission ? 3 : 2;
                ctx.beginPath();
                ctx.moveTo(projected[0].x, projected[0].y);
                for (let i = 1; i < projected.length; i++) ctx.lineTo(projected[i].x, projected[i].y);
                ctx.stroke();
                for (let i = 0; i < projected.length - 1; i++) drawArrowHead(projected[i], projected[i + 1], color, 1.1);
            } else if (mission.mode === "SPIN_360" && projected.length) {
                const p = projected[0];
                ctx.strokeStyle = color;
                ctx.lineWidth = 3;
                ctx.beginPath();
                ctx.arc(p.x, p.y, 15, 0, Math.PI * 2);
                ctx.stroke();
            }
            const metricScale = Math.max(Number(geometry.radius) * 0.08, 0.25);
            (mission.waypoints || []).forEach((point, pointIndex) => {
                const p = projectPerspective(point);
                if (!p) return;
                ctx.fillStyle = color;
                ctx.strokeStyle = missionIndex === state.activeMission && pointIndex === state.selectedPoint ? "#fff" : "#202020";
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();

                if (mission.mode === "PATH") {
                    const tip = projectPerspective(orientationTip(point, mission, pointIndex, metricScale));
                    if (tip) {
                        ctx.strokeStyle = "#f5f5f5";
                        ctx.lineWidth = 1.5;
                        ctx.beginPath();
                        ctx.moveTo(p.x, p.y);
                        ctx.lineTo(tip.x, tip.y);
                        ctx.stroke();
                        drawArrowHead(p, tip, "#f5f5f5", 0.8);
                    }
                }
            });
            if (missionIndex === state.activeMission && state.selectedPoint != null) {
                drawSelectedFrustum(projectPerspective, mission, state.selectedPoint, color);
            }
            if (mission.orientation_mode === "LOOK_AT_TARGET") {
                drawTargetMarker(projectPerspective, mission.look_target, color);
            }
        }

        ctx.restore();
        ctx.fillStyle = "#aaa";
        ctx.font = "11px sans-serif";
        ctx.fillText("drag: orbit · Shift+drag: pan · wheel / −/+ : zoom · inspection only · " + state.previewMode, plot.x + 8, plot.y + plot.height - 10);
    }

    function pointFromPanel(panel, x, y, base) {
        return worldFromPanel(panel, x, y, base);
    }

    function eventCoordinates(event) {
        const rect = canvas.getBoundingClientRect();
        if (!rect.width || !rect.height) return null;
        return {
            x: (event.clientX - rect.left) * canvas.width / rect.width,
            y: (event.clientY - rect.top) * canvas.height / rect.height,
        };
    }

    function nearestPoint(panel, x, y) {
        const mission = activeMission();
        if (!mission) return null;
        let best = null;
        let bestDistance = 14;
        (mission.waypoints || []).forEach((point, index) => {
            const p = project(panel, point);
            const distance = Math.hypot(p.x - x, p.y - y);
            if (distance < bestDistance) {
                best = index;
                bestDistance = distance;
            }
        });
        return best;
    }

    function nearestPerspectivePoint(x, y) {
        const mission = activeMission();
        if (!mission) return null;
        let best = null;
        let bestDistance = 14;
        (mission.waypoints || []).forEach((point, index) => {
            const p = projectPerspective(point);
            if (!p) return;
            const distance = Math.hypot(p.x - x, p.y - y);
            if (distance < bestDistance) {
                best = index;
                bestDistance = distance;
            }
        });
        return best;
    }

    function collisionMissionReport(mission) {
        if (state.collisionStale) return null;
        const reports = state.metadata?.collision_preflight?.missions;
        if (!Array.isArray(reports)) return null;
        return reports.find((item) => item.mission_name === mission.name) || null;
    }

    function blockedSegment(report, index) {
        if (!report?.segments) return false;
        const segment = report.segments.find((item) => Number(item.segment_index) === index);
        return Boolean(segment?.blocked);
    }

    function canvasDimensionsFromProjection() {
        const rects = [
            state.projection?.perspective_panel?.panel_rect_px,
            ...(state.projection?.panels || []).map((panel) => panel.panel_rect_px),
        ].filter(Boolean);
        if (!rects.length) return { width: 900, height: 900 };
        return {
            width: Math.ceil(Math.max(...rects.map((r) => r.x + r.width)) + 10),
            height: Math.ceil(Math.max(...rects.map((r) => r.y + r.height)) + 10),
        };
    }

    function drawPanelShell(panel, subtitle) {
        const rect = panel.panel_rect_px;
        const plot = panel.plot_rect_px;
        ctx.fillStyle = "#181818";
        ctx.fillRect(rect.x, rect.y, rect.width, rect.height);
        ctx.strokeStyle = "#555";
        ctx.lineWidth = 1;
        ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);
        ctx.strokeStyle = "#333";
        ctx.strokeRect(plot.x, plot.y, plot.width, plot.height);
        ctx.fillStyle = "#eee";
        ctx.font = "12px sans-serif";
        ctx.fillText(panel.name || "", rect.x + 10, rect.y + 16);
        ctx.fillStyle = "#999";
        ctx.font = "10px sans-serif";
        ctx.fillText(subtitle || "", rect.x + 10, rect.y + 31);
    }

    function geometryPoint(raw) {
        return { right: Number(raw[0]), up: Number(raw[1]), forward: Number(raw[2]) };
    }

    function drawOrthographicScene(panel) {
        const geometry = state.metadata?.preview_geometry;
        if (!geometry?.points) return;
        const plot = panel.plot_rect_px;
        ctx.save();
        ctx.beginPath();
        ctx.rect(plot.x, plot.y, plot.width, plot.height);
        ctx.clip();

        if (String(state.previewMode).startsWith("MESH_")) {
            ctx.restore();
            drawOrthographicMesh(panel, state.previewMode);
            ctx.save();
            ctx.beginPath();
            ctx.rect(plot.x, plot.y, plot.width, plot.height);
            ctx.clip();
        } else {
            const points = activePointLod().points || [];
            const drawStride = Math.max(1, Math.ceil(points.length / GEOMETRY_DRAW_BUDGET));
            const size = Math.max(0.5, Math.min(4.0, Number(state.pointSize) || 1.25));
            for (let index = 0; index < points.length; index += drawStride) {
                const raw = points[index];
                const p = project(panel, geometryPoint(raw));
                if (p.x < plot.x || p.x > plot.x + plot.width || p.y < plot.y || p.y > plot.y + plot.height) continue;
                ctx.fillStyle = `rgba(${raw[3] ?? 150},${raw[4] ?? 150},${raw[5] ?? 150},0.78)`;
                ctx.fillRect(p.x - size * 0.5, p.y - size * 0.5, size, size);
            }
        }
        ctx.restore();

        const extent = orthoExtent(panel);
        ctx.fillStyle = "#999";
        ctx.font = "10px sans-serif";
        ctx.fillText(
            `zoom ${extent.view.zoom.toFixed(2)}x · ${state.previewMode} · Shift+drag/middle = pan · wheel / −/+ = zoom`,
            plot.x + 7, plot.y + plot.height - 8
        );
    }

    function draw() {
        if (!canvas.width || !canvas.height) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "#111";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        if (!validPlan(state.plan) || !state.projection) return;

        const perspective = perspectivePanel();
        if (perspective) {
            drawPanelShell(perspective, "ORBIT / PAN / ZOOM · inspection");
            drawPerspectiveScene();
        }
        for (const panel of state.projection.panels || []) {
            drawPanelShell(panel, `${String(panel.x_axis).toUpperCase()} / ${String(panel.y_axis).toUpperCase()} · axis locked`);
            drawOrthographicScene(panel);
        }

        if (perspective) drawZoomControls(perspective);
        for (const panel of state.projection.panels || []) drawZoomControls(panel);

        for (let missionIndex = 0; missionIndex < state.plan.missions.length; missionIndex++) {
            const mission = state.plan.missions[missionIndex];
            if (mission.enabled === false) continue;
            const color = COLORS[missionIndex % COLORS.length];
            const points = mission.waypoints || [];

            for (const panel of state.projection.panels || []) {
                const plot = panel.plot_rect_px;
                ctx.save();
                ctx.beginPath();
                ctx.rect(plot.x, plot.y, plot.width, plot.height);
                ctx.clip();

                const projected = points.map((point) => project(panel, point));
                const collisionReport = collisionMissionReport(mission);
                if (mission.mode === "PATH" && projected.length > 1) {
                    for (let segmentIndex = 0; segmentIndex < projected.length - 1; segmentIndex++) {
                        const blocked = blockedSegment(collisionReport, segmentIndex);
                        const a = projected[segmentIndex];
                        const b = projected[segmentIndex + 1];
                        ctx.strokeStyle = blocked ? "#ff3b58" : color;
                        ctx.lineWidth = blocked ? 4 : (missionIndex === state.activeMission ? 2.5 : 1.5);
                        ctx.setLineDash(blocked ? [10, 5] : (missionIndex === state.activeMission ? [] : [7, 5]));
                        ctx.beginPath();
                        ctx.moveTo(a.x, a.y);
                        ctx.lineTo(b.x, b.y);
                        ctx.stroke();
                        drawArrowHead(a, b, blocked ? "#ff3b58" : color, blocked ? 1.0 : 0.85);
                    }
                    ctx.setLineDash([]);
                }

                if (mission.mode === "SPIN_360" && projected.length) {
                    const p = projected[0];
                    const blocked = Boolean(collisionReport?.blocked);
                    ctx.strokeStyle = blocked ? "#ff3b58" : color;
                    ctx.lineWidth = blocked ? 4 : 2.5;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, 11, 0, Math.PI * 2);
                    ctx.stroke();
                }

                const extent = orthoExtent(panel);
                const metricSpan = Math.max(extent.spanX, extent.spanY);
                points.forEach((point, pointIndex) => {
                    const p = projected[pointIndex];
                    const selectedPoint =
                        missionIndex === state.activeMission && pointIndex === state.selectedPoint;
                    ctx.fillStyle = color;
                    ctx.strokeStyle = selectedPoint ? "#ffffff" : "#202020";
                    ctx.lineWidth = selectedPoint ? 2 : 1;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, selectedPoint ? 5 : 3.5, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.stroke();
                    ctx.fillStyle = color;
                    ctx.font = "10px sans-serif";
                    ctx.fillText(String(pointIndex + 1), p.x + 6, p.y - 5);

                    if (mission.mode === "PATH") {
                        const tipPoint = orientationTip(point, mission, pointIndex, Math.max(metricSpan * 0.035, 0.15));
                        const tip = project(panel, tipPoint);
                        ctx.strokeStyle = "#f5f5f5";
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(p.x, p.y);
                        ctx.lineTo(tip.x, tip.y);
                        ctx.stroke();
                        drawArrowHead(p, tip, "#f5f5f5", 0.65);
                    }
                });
                if (missionIndex === state.activeMission && state.selectedPoint != null) {
                    drawSelectedFrustum((point) => project(panel, point), mission, state.selectedPoint, color);
                }
                if (mission.orientation_mode === "LOOK_AT_TARGET") {
                    drawTargetMarker((point) => project(panel, point), mission.look_target, color);
                }
                ctx.restore();
            }
        }
        drawSelectedCameraView();
    }

    function resetViewportFraming() {
        if (!state.projection) return;
        ensureOrthoViews(true);
        const perspective = state.projection?.perspective_panel;
        state.orbitYaw = Number(perspective?.default_yaw_deg ?? -35) * Math.PI / 180;
        state.orbitPitch = Number(perspective?.default_pitch_deg ?? -18) * Math.PI / 180;
        state.orbitZoom = Number(perspective?.default_zoom ?? 1);
        state.orbitPanX = 0;
        state.orbitPanY = 0;
        ensureRouteVisible();
        draw();
    }

    function ingestExecution(message) {
        const raw = message?.route_editor;
        const meta = Array.isArray(raw) ? raw[0] : raw;
        if (!meta?.projection || !meta?.plan) return;
        sanitizeNumericWidgets();
        const sceneKey = String(meta?.diagnostics?.scene_contract_id || meta?.diagnostics?.source_run_id || "");
        const sceneChanged = Boolean(sceneKey && state.sceneKey && sceneKey !== state.sceneKey);
        state.sceneKey = sceneKey || state.sceneKey;
        state.metadata = meta;
        state.projection = meta.projection;
        state.collisionStale = false;
        const cameraMeta = meta.camera_preview_contract;
        if (cameraMeta?.width && cameraMeta?.height) {
            cameraPreviewCanvas.width = 640;
            cameraPreviewCanvas.height = Math.max(180, Math.round(640 * Number(cameraMeta.height) / Number(cameraMeta.width)));
        }

        const size = canvasDimensionsFromProjection();
        canvas.width = size.width;
        canvas.height = size.height;

        const needsInitialFraming = sceneChanged || !Object.keys(state.orthoViews).length;
        if (needsInitialFraming) {
            ensureOrthoViews(true);
            resetViewportFraming();
        } else {
            ensureOrthoViews(false);
        }

        const cleanPlan = clone(meta.plan);
        delete cleanPlan.route_plan_dirty;
        if (!state.initialSeedPlan || sceneChanged || String(cleanPlan.route_authority || "").toUpperCase() === "EDITABLE_SEED") {
            state.initialSeedPlan = clone(cleanPlan);
        }
        setPlan(cleanPlan, true);
        if (needsInitialFraming) ensureRouteVisible();
        state.collisionStale = false;
        updateToolbar();
        draw();
    }

    function portableRoutePreset() {
        if (!validPlan(state.plan)) return null;
        sanitizeNumericWidgets();
        return {
            schema: ROUTE_PRESET_SCHEMA,
            coordinate_space: "P9_CAMERA_LOCAL_RIGHT_UP_FORWARD_METERS",
            exported_at_utc: new Date().toISOString(),
            source_scene_contract_id: state.plan.scene_contract_id || null,
            source_run_id: state.plan.source_run_id || null,
            frames_per_drone: Math.max(2, Math.min(240, Math.round(Number(framesWidget?.value ?? state.plan.frames_per_drone ?? 30)))),
            collision_mode: String(state.plan.collision_mode || "HOLD_AND_RESUME"),
            min_clearance_m: Math.max(0, Math.min(10, Number(clearanceWidget?.value ?? state.plan.min_clearance_m ?? 0.20))),
            missions: clone(state.plan.missions),
        };
    }

    function validateImportedPreset(payload) {
        const route = payload;
        if (!route || !Array.isArray(route.missions) || route.missions.length < 1 || route.missions.length > 7) {
            throw new Error("Arquivo de trajeto inválido: missions deve conter 1–7 drones.");
        }
        if (route.coordinate_space && route.coordinate_space !== "P9_CAMERA_LOCAL_RIGHT_UP_FORWARD_METERS") {
            throw new Error("Arquivo usa um coordinate_space incompatível.");
        }
        const finitePoint = (point) =>
            point && ["right", "up", "forward"].every((key) => Number.isFinite(Number(point[key])));
        route.missions.forEach((mission, missionIndex) => {
            const mode = String(mission?.mode || "PATH").toUpperCase();
            if (!["PATH", "SPIN_360"].includes(mode)) throw new Error(`Drone ${missionIndex + 1}: modo inválido.`);
            if (!Array.isArray(mission.waypoints)) throw new Error(`Drone ${missionIndex + 1}: waypoints ausentes.`);
            if (mode === "PATH" && mission.waypoints.length < 2) throw new Error(`Drone ${missionIndex + 1}: PATH precisa de pelo menos 2 pontos.`);
            if (mode === "SPIN_360" && mission.waypoints.length !== 1) throw new Error(`Drone ${missionIndex + 1}: 360° precisa de 1 ponto.`);
            if (!mission.waypoints.every(finitePoint)) throw new Error(`Drone ${missionIndex + 1}: waypoint inválido.`);
            const orientation = String(mission.orientation_mode || "LOOK_ALONG_PATH").toUpperCase();
            if (!["LOOK_AT_TARGET", "LOOK_ALONG_PATH", "MANUAL_DIRECTION"].includes(orientation)) {
                throw new Error(`Drone ${missionIndex + 1}: orientação inválida.`);
            }
            if (mode === "PATH" && orientation === "LOOK_AT_TARGET" && !finitePoint(mission.look_target)) {
                throw new Error(`Drone ${missionIndex + 1}: LOOK_AT_TARGET sem alvo válido.`);
            }
            if (mode === "PATH" && orientation === "MANUAL_DIRECTION" && !finitePoint(mission.manual_direction)) {
                throw new Error(`Drone ${missionIndex + 1}: MANUAL_DIRECTION inválida.`);
            }
        });
        return route;
    }

    function exportRoutePreset() {
        const preset = portableRoutePreset();
        if (!preset) return;
        const blob = new Blob([JSON.stringify(preset, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        const run = String(state.plan?.source_run_id || "route").replace(/[^A-Za-z0-9._-]+/g, "_");
        link.href = url;
        link.download = `ConceptGhost_drone_route_${run}.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        status.textContent = "Trajeto exportado · JSON portátil salvo";
        status.style.color = "#86e276";
    }

    async function importRoutePresetFile(file) {
        if (!file || !validPlan(state.plan)) return;
        const payload = validateImportedPreset(JSON.parse(await file.text()));
        pushHistory();

        const previousScene = String(payload.source_scene_contract_id || "");
        const currentScene = String(state.plan.scene_contract_id || "");
        const imported = {
            ...clone(state.plan),
            missions: clone(payload.missions),
            frames_per_drone: Math.max(2, Math.min(240, Math.round(Number(payload.frames_per_drone ?? 30)))),
            collision_mode: String(payload.collision_mode || "HOLD_AND_RESUME").toUpperCase(),
            min_clearance_m: Math.max(0, Math.min(10, Number(payload.min_clearance_m ?? 0.20))),
            route_authority: "ARTIST_AUTHORED",
            route_plan_dirty: true,
        };
        delete imported.route_plan_sha256;

        if (framesWidget) framesWidget.value = imported.frames_per_drone;
        if (clearanceWidget) clearanceWidget.value = imported.min_clearance_m;
        state.plan = imported;
        state.activeMission = 0;
        state.selectedPoint = null;
        state.editingTarget = false;
        state.targetDragging = false;
        persist();
        ensureRouteVisible();
        draw();

        const crossScene = previousScene && currentScene && previousScene !== currentScene;
        status.textContent = crossScene
            ? `Trajeto importado de outra cena · ${imported.missions.length} drone(s) · revise posições antes do Run`
            : `Trajeto importado · ${imported.missions.length} drone(s) · pronto para revisar`;
        status.style.color = crossScene ? "#ffdc5a" : "#86e276";
    }

    canvas.addEventListener("pointerdown", (event) => {
        if (!state.projection || !validPlan(state.plan)) return;
        const xy = eventCoordinates(event);
        if (!xy) return;

        const zoomControl = hitZoomControl(xy.x, xy.y);
        if (zoomControl) {
            event.preventDefault();
            event.stopPropagation();
            const factor = zoomControl.action === "in" ? 1.35 : (1 / 1.35);
            applyPanelZoom(zoomControl.panel, factor);
            return;
        }

        const perspective = perspectivePanel();
        const panGesture = event.shiftKey || event.button === 1;

        if (perspective && insideRect(perspective.plot_rect_px, xy.x, xy.y)) {
            if (!panGesture) {
                const hit = nearestPerspectivePoint(xy.x, xy.y);
                if (hit != null) {
                    state.selectedPoint = hit;
                    updateToolbar();
                    draw();
                    event.preventDefault();
                    return;
                }
            }
            state.orbitLast = xy;
            if (panGesture) state.orbitPanning = true;
            else state.orbitDragging = true;
            canvas.setPointerCapture?.(event.pointerId);
            canvas.style.cursor = panGesture ? "move" : "grabbing";
            event.preventDefault();
            return;
        }

        const panel = panelAt(xy.x, xy.y);
        if (!panel) return;
        if (panGesture) {
            state.orthoPanning = true;
            state.orthoPanPanel = panel.name;
            state.orthoLast = xy;
            canvas.setPointerCapture?.(event.pointerId);
            canvas.style.cursor = "move";
            event.preventDefault();
            return;
        }

        const mission = activeMission();
        if (!mission) return;

        if (state.editingTarget && mission.mode === "PATH") {
            pushHistory();
            const base = mission.look_target || defaultPoint(state.projection);
            mission.look_target = pointFromPanel(panel, xy.x, xy.y, base);
            mission.orientation_mode = "LOOK_AT_TARGET";
            state.selectedPoint = null;
            state.targetDragging = true;
            state.dragHistoryPushed = true;
            canvas.setPointerCapture?.(event.pointerId);
            persist();
            return;
        }

        const hit = nearestPoint(panel, xy.x, xy.y);
        if (hit != null) {
            state.selectedPoint = hit;
            state.dragging = true;
            state.dragHistoryPushed = false;
            canvas.setPointerCapture?.(event.pointerId);
            updateToolbar();
            draw();
            return;
        }

        pushHistory();
        const points = mission.waypoints || (mission.waypoints = []);
        const base = points[points.length - 1] || defaultPoint(state.projection);
        const point = pointFromPanel(panel, xy.x, xy.y, base);

        if (mission.mode === "SPIN_360") {
            mission.waypoints = [point];
            state.selectedPoint = 0;
        } else {
            mission.waypoints.push(point);
            state.selectedPoint = mission.waypoints.length - 1;
        }
        persist();
    });

    canvas.addEventListener("pointermove", (event) => {
        const xy = eventCoordinates(event);
        if (!xy) return;

        if ((state.orbitDragging || state.orbitPanning) && state.orbitLast) {
            const dx = xy.x - state.orbitLast.x;
            const dy = xy.y - state.orbitLast.y;
            if (state.orbitPanning) {
                state.orbitPanX += dx;
                state.orbitPanY += dy;
            } else {
                state.orbitYaw += dx * 0.008;
                state.orbitPitch = Math.max(-1.35, Math.min(1.35, state.orbitPitch + dy * 0.008));
            }
            state.orbitLast = xy;
            draw();
            return;
        }

        if (state.orthoPanning && state.orthoLast && state.orthoPanPanel) {
            const panel = (state.projection?.panels || []).find((item) => item.name === state.orthoPanPanel);
            if (panel) {
                const extent = orthoExtent(panel);
                const dx = xy.x - state.orthoLast.x;
                const dy = xy.y - state.orthoLast.y;
                extent.view.panX -= dx / panel.plot_rect_px.width * extent.spanX;
                extent.view.panY += dy / panel.plot_rect_px.height * extent.spanY;
                state.orthoLast = xy;
                draw();
            }
            return;
        }

        if (!state.dragging && !state.targetDragging) return;
        if (!state.targetDragging && state.selectedPoint == null) return;
        const panel = panelAt(xy.x, xy.y);
        if (!panel) return;
        const mission = activeMission();
        if (state.targetDragging && mission?.look_target) {
            mission.look_target = pointFromPanel(panel, xy.x, xy.y, mission.look_target);
            persist();
            return;
        }
        const point = mission?.waypoints?.[state.selectedPoint];
        if (!point) return;

        if (!state.dragHistoryPushed) {
            pushHistory();
            state.dragHistoryPushed = true;
        }
        mission.waypoints[state.selectedPoint] = pointFromPanel(panel, xy.x, xy.y, point);
        persist();
    });

    const stopDrag = (event) => {
        const wasEditing = state.dragging || state.targetDragging;
        if (!wasEditing && !state.orbitDragging && !state.orbitPanning && !state.orthoPanning) return;
        state.dragging = false;
        state.targetDragging = false;
        state.dragHistoryPushed = false;
        state.orbitDragging = false;
        state.orbitPanning = false;
        state.orbitLast = null;
        state.orthoPanning = false;
        state.orthoPanPanel = null;
        state.orthoLast = null;
        canvas.style.cursor = "crosshair";
        canvas.releasePointerCapture?.(event.pointerId);
        if (wasEditing) {
            // Keep the exact zoom/pan used to place the point.
            draw();
        }
    };
    canvas.addEventListener("pointerup", stopDrag);
    canvas.addEventListener("pointercancel", stopDrag);

    // Capture wheel events inside the DOM editor before the ComfyUI graph canvas
    // can interpret them as workspace zoom. Explicit −/+ controls remain available
    // in every view as a deterministic fallback.
    root.addEventListener("wheel", (event) => {
        if (!state.projection) return;
        if (event.target !== canvas && !canvas.contains?.(event.target)) return;
        const xy = eventCoordinates(event);
        if (!xy) return;
        const factor = Math.exp(-event.deltaY * 0.0015);
        if (!zoomAtCanvasPoint(xy, factor)) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation?.();
    }, { passive: false, capture: true });

    canvas.addEventListener("contextmenu", (event) => {
        const xy = eventCoordinates(event);
        if (!xy) return;
        if ((perspectivePanel() && insideRect(perspectivePanel().plot_rect_px, xy.x, xy.y)) || panelAt(xy.x, xy.y)) {
            if (event.shiftKey) event.preventDefault();
        }
    });

    previewModeSelect.addEventListener("change", () => {
        const requested = PREVIEW_MODES.includes(previewModeSelect.value) ? previewModeSelect.value : "POINTS_MEDIUM";
        if (requested.startsWith("MESH_") && !activeMeshLod()) {
            state.previewMode = "POINTS_MEDIUM";
            previewModeSelect.value = state.previewMode;
            status.textContent = "Mesh visual indisponível neste PrimaryMesh · usando Points Medium";
            status.style.color = "#ffdc5a";
        } else {
            state.previewMode = requested;
        }
        pointSizeInput.disabled = state.previewMode.startsWith("MESH_");
        draw();
    });

    pointSizeInput.addEventListener("input", () => {
        const value = Number(pointSizeInput.value);
        state.pointSize = Math.max(0.5, Math.min(4.0, Number.isFinite(value) ? value : 1.25));
        pointSizeValue.textContent = state.pointSize.toFixed(2) + " px";
        draw();
    });

    droneSelect.addEventListener("change", () => {
        state.activeMission = Number(droneSelect.value) || 0;
        state.selectedPoint = null;
        state.editingTarget = false;
        updateToolbar();
        draw();
    });


    orientationSelect.addEventListener("change", () => {
        const mission = activeMission();
        if (!mission || mission.mode === "SPIN_360") return;
        pushHistory();
        mission.orientation_mode = orientationSelect.value;
        if (mission.orientation_mode === "LOOK_AT_TARGET" && !mission.look_target) {
            mission.look_target = defaultPoint(state.projection);
        }
        if (mission.orientation_mode === "MANUAL_DIRECTION" && !mission.manual_direction) {
            mission.manual_direction = { right: 0, up: 0, forward: 1 };
        }
        state.editingTarget = false;
        persist();
    });

    editTarget.addEventListener("click", () => {
        const mission = activeMission();
        if (!mission || mission.mode === "SPIN_360") return;
        pushHistory();
        mission.orientation_mode = "LOOK_AT_TARGET";
        if (!mission.look_target) mission.look_target = defaultPoint(state.projection);
        state.editingTarget = !state.editingTarget;
        state.targetDragging = false;
        state.selectedPoint = null;
        persist();
    });

    const manualChanged = () => {
        const mission = activeMission();
        if (!mission || mission.mode === "SPIN_360") return;
        pushHistory();
        mission.orientation_mode = "MANUAL_DIRECTION";
        mission.manual_direction = manualDirectionFromInputs();
        state.editingTarget = false;
        persist();
    };
    yawInput.addEventListener("change", manualChanged);
    pitchInput.addEventListener("change", manualChanged);

    modeSelect.addEventListener("change", () => {
        const mission = activeMission();
        if (!mission) return;
        pushHistory();
        const mode = modeSelect.value;
        if (mode === "SPIN_360") {
            mission.mode = "SPIN_360";
            mission.waypoints = [mission.waypoints?.[0] || defaultPoint(state.projection)];
            state.selectedPoint = 0;
        } else {
            mission.mode = "PATH";
            if (!mission.orientation_mode || mission.orientation_mode === "SPIN_360") {
                mission.orientation_mode = "LOOK_AT_TARGET";
            }
            if (mission.orientation_mode === "LOOK_AT_TARGET" && !mission.look_target) {
                mission.look_target = defaultPoint(state.projection);
            }
            if (!mission.waypoints?.length) {
                mission.waypoints = seedPath(state.projection);
            } else if (mission.waypoints.length === 1) {
                const seed = seedPath(state.projection);
                seed[0] = clone(mission.waypoints[0]);
                mission.waypoints = seed;
            }
            state.selectedPoint = 0;
        }
        persist();
    });

    addDrone.addEventListener("click", () => {
        if (!validPlan(state.plan) || state.plan.missions.length >= 7) return;
        pushHistory();
        const index = state.plan.missions.length;
        state.plan.missions.push({
            name: `drone_${index + 1}`,
            mode: "PATH",
            enabled: true,
            orientation_mode: "LOOK_AT_TARGET",
            look_target: defaultPoint(state.projection),
            manual_direction: { right: 0, up: 0, forward: 1 },
            waypoints: seedPath(state.projection),
        });
        state.activeMission = index;
        state.selectedPoint = 0;
        persist();
    });

    removeDrone.addEventListener("click", () => {
        if (!validPlan(state.plan) || state.plan.missions.length <= 1) return;
        pushHistory();
        state.plan.missions.splice(state.activeMission, 1);
        state.plan.missions.forEach((mission, index) => {
            mission.name = `drone_${index + 1}`;
        });
        state.activeMission = Math.max(0, state.activeMission - 1);
        state.selectedPoint = null;
        state.editingTarget = false;
        persist();
    });

    deletePoint.addEventListener("click", () => {
        const mission = activeMission();
        if (!mission || state.selectedPoint == null) return;
        pushHistory();
        mission.waypoints.splice(state.selectedPoint, 1);
        state.selectedPoint = mission.waypoints.length
            ? Math.min(state.selectedPoint, mission.waypoints.length - 1)
            : null;
        persist();
    });

    clearRoute.addEventListener("click", () => {
        const mission = activeMission();
        if (!mission) return;
        pushHistory();
        mission.waypoints = [];
        state.selectedPoint = null;
        persist();
    });

    undo.addEventListener("click", () => {
        const previous = state.history.pop();
        if (!previous) return;
        setPlan(previous, true);
    });

    resetRoute.addEventListener("click", () => {
        if (!state.initialSeedPlan || !state.projection || !state.metadata) {
            status.textContent = "A cena ainda não foi carregada. Execute Run #1 primeiro.";
            status.style.color = "#ffdc5a";
            return;
        }
        sanitizeNumericWidgets();
        pushHistory();
        state.history = [];
        state.selectedPoint = null;
        state.editingTarget = false;
        state.targetDragging = false;
        state.collisionStale = true;
        setPlan(clone(state.initialSeedPlan), true);
        status.textContent = "Rota restaurada para a semente desta cena · zoom/pan preservados";
        status.style.color = "#ffdc5a";
        node.graph?.setDirtyCanvas?.(true, true);
        draw();
    });

    exportRoute.addEventListener("click", () => {
        try {
            exportRoutePreset();
        } catch (error) {
            status.textContent = "Falha ao exportar trajeto: " + String(error?.message || error);
            status.style.color = "#ff6868";
        }
    });

    importRoute.addEventListener("click", () => {
        importInput.value = "";
        importInput.click();
    });

    importInput.addEventListener("change", async () => {
        const file = importInput.files?.[0];
        if (!file) return;
        try {
            await importRoutePresetFile(file);
        } catch (error) {
            status.textContent = "Falha ao importar trajeto: " + String(error?.message || error);
            status.style.color = "#ff6868";
        } finally {
            importInput.value = "";
        }
    });

    frameAll.addEventListener("click", () => {
        resetViewportFraming();
        status.textContent = "Enquadramento restaurado · rota e P9 não foram alterados";
        status.style.color = "#86e276";
    });

    chainCallback(node, "onExecuted", function (message) {
        ingestExecution(message);
    });

    // Restore the serialized route immediately when a workflow is reopened.
    sanitizeNumericWidgets();
    try {
        const saved = JSON.parse(String(routeWidget.value || "").trim());
        if (validPlan(saved)) {
            setPlan(saved, false);
            state.collisionStale = true;
            updateToolbar();
        }
    } catch (_) {
        // First execution will seed a valid plan.
    }

    updateToolbar();
}

app.registerExtension({
    name: "ConceptGhost.P10.ArtistDroneRouteEditor",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_CLASS) return;
        const original = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            original?.apply(this, arguments);
            setupEditor(this);
        };
    },
});

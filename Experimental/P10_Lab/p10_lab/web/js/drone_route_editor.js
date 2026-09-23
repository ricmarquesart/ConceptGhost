import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_CLASS = "ConceptGhostP10DroneRouteAuthoring";
const COLORS = ["#ffb040", "#4ebeff", "#86e276", "#de76ff", "#ff6868", "#ffdc5a", "#5ee8d4"];

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
    }
    return { ok: true, text: `${active.length} drone(s) ativo(s) · plano válido` };
}

function setupEditor(node) {
    if (node.__cgRouteEditorInstalled) return;
    node.__cgRouteEditorInstalled = true;

    const routeWidget = findWidget(node, "route_plan_json");
    if (!routeWidget) return;

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
        "height:1080px",
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
    const resetScene = button("Resetar cena", "Descartar a rota salva e gerar uma nova semente para a cena atual");

    toolbar.append("Drone:", droneSelect, modeSelect, addDrone, removeDrone, deletePoint, undo, clearRoute, resetScene);

    const help = document.createElement("div");
    help.textContent =
        "PERSPECTIVE: arraste para orbitar e use a roda para zoom. TOP, SIDE e FRONT editam o mesmo ponto 3D " +
        "com escala métrica preservada. A perspectiva é inspeção, sem criação ambígua de profundidade. " +
        "Após editar, execute Queue Prompt para aplicar a rota ao P10.";
    help.style.cssText = "color:#aaa;line-height:1.3;";

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

    root.append(toolbar, help, canvasWrap, footer);

    node.addDOMWidget("cg_drone_route_editor", "route_editor", root, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 900,
        getHeight: () => 1080,
    });

    node.setSize?.([Math.max(node.size?.[0] || 900, 1180), Math.max(node.size?.[1] || 900, 1250)]);

    const ctx = canvas.getContext("2d");
    const state = {
        plan: null,
        projection: null,
        background: null,
        activeMission: 0,
        selectedPoint: null,
        dragging: false,
        dragHistoryPushed: false,
        history: [],
        metadata: null,
        collisionStale: false,
        orbitYaw: -35 * Math.PI / 180,
        orbitPitch: -18 * Math.PI / 180,
        orbitZoom: 1.0,
        orbitDragging: false,
        orbitLast: null,
    };

    function pushHistory() {
        if (!validPlan(state.plan)) return;
        state.history.push(clone(state.plan));
        if (state.history.length > 40) state.history.shift();
    }

    function persist() {
        if (!validPlan(state.plan)) return;
        state.plan.route_authority = "ARTIST_AUTHORED";
        delete state.plan.route_plan_sha256;
        state.plan.route_plan_dirty = true;
        routeWidget.value = JSON.stringify(state.plan, null, 2);
        routeWidget.callback?.(routeWidget.value);
        state.collisionStale = true;
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
                ? "Nenhum ponto selecionado"
                : `Ponto ${state.selectedPoint + 1}`;
    }

    function panelAt(x, y) {
        return (state.projection?.panels || []).find((panel) => {
            const r = panel.plot_rect_px;
            return x >= r.x && x <= r.x + r.width && y >= r.y && y <= r.y + r.height;
        }) || null;
    }

    function project(panel, point) {
        const r = panel.plot_rect_px;
        const xExtent = panel.x_extent;
        const yExtent = panel.y_extent;
        const xValue = Number(point[panel.x_axis]);
        const yValue = Number(point[panel.y_axis]);
        const xAmount = (xValue - Number(xExtent.min)) / (Number(xExtent.max) - Number(xExtent.min));
        const yAmount = (yValue - Number(yExtent.min)) / (Number(yExtent.max) - Number(yExtent.min));
        return {
            x: r.x + xAmount * r.width,
            y: r.y + (1 - yAmount) * r.height,
        };
    }


    function perspectivePanel() {
        return state.projection?.perspective_panel || null;
    }

    function insideRect(rect, x, y) {
        return Boolean(rect) &&
            x >= rect.x && x <= rect.x + rect.width &&
            y >= rect.y && y <= rect.y + rect.height;
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
            x: plot.x + plot.width * 0.5 + (x1 / depth) * focal,
            y: plot.y + plot.height * 0.5 - (y2 / depth) * focal,
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

    function drawPerspectiveScene() {
        const panel = perspectivePanel();
        const geometry = state.metadata?.preview_geometry;
        if (!panel || !geometry?.points) return;
        const plot = panel.plot_rect_px;

        ctx.save();
        ctx.beginPath();
        ctx.rect(plot.x, plot.y, plot.width, plot.height);
        ctx.clip();

        const points = geometry.points;
        const drawStride = Math.max(1, Math.ceil(points.length / 9000));
        for (let index = 0; index < points.length; index += drawStride) {
            const raw = points[index];
            const p = projectPerspective(raw);
            if (!p) continue;
            if (p.x < plot.x || p.x > plot.x + plot.width || p.y < plot.y || p.y > plot.y + plot.height) continue;
            ctx.fillStyle = `rgba(${raw[3] ?? 150},${raw[4] ?? 150},${raw[5] ?? 150},0.72)`;
            ctx.fillRect(p.x, p.y, 1.4, 1.4);
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
            projected.forEach((p, pointIndex) => {
                ctx.fillStyle = color;
                ctx.strokeStyle = missionIndex === state.activeMission && pointIndex === state.selectedPoint ? "#fff" : "#202020";
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();
            });
        }

        ctx.restore();
        ctx.fillStyle = "#aaa";
        ctx.font = "11px sans-serif";
        ctx.fillText("drag: orbit · wheel: zoom · inspection only", plot.x + 8, plot.y + plot.height - 10);
    }

    function pointFromPanel(panel, x, y, base) {
        const r = panel.plot_rect_px;
        const xExtent = panel.x_extent;
        const yExtent = panel.y_extent;
        const xAmount = Math.max(0, Math.min(1, (x - r.x) / r.width));
        const yAmount = Math.max(0, Math.min(1, 1 - (y - r.y) / r.height));
        const point = { ...base };
        point[panel.x_axis] = Number(xExtent.min) + xAmount * (Number(xExtent.max) - Number(xExtent.min));
        point[panel.y_axis] = Number(yExtent.min) + yAmount * (Number(yExtent.max) - Number(yExtent.min));
        return point;
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

    function draw() {
        if (!canvas.width || !canvas.height) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "#111";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        if (state.background?.complete && state.background.naturalWidth) {
            ctx.drawImage(state.background, 0, 0, canvas.width, canvas.height);
        }

        if (!validPlan(state.plan) || !state.projection) return;

        drawPerspectiveScene();

        for (let missionIndex = 0; missionIndex < state.plan.missions.length; missionIndex++) {
            const mission = state.plan.missions[missionIndex];
            if (mission.enabled === false) continue;
            const color = COLORS[missionIndex % COLORS.length];
            const points = mission.waypoints || [];

            for (const panel of state.projection.panels || []) {
                const projected = points.map((point) => project(panel, point));

                const collisionReport = collisionMissionReport(mission);
                if (mission.mode === "PATH" && projected.length > 1) {
                    for (let segmentIndex = 0; segmentIndex < projected.length - 1; segmentIndex++) {
                        const blocked = blockedSegment(collisionReport, segmentIndex);
                        const a = projected[segmentIndex];
                        const b = projected[segmentIndex + 1];
                        ctx.strokeStyle = blocked ? "#ff3b58" : color;
                        ctx.lineWidth = blocked ? 5 : (missionIndex === state.activeMission ? 3 : 2);
                        ctx.setLineDash(blocked ? [10, 5] : (missionIndex === state.activeMission ? [] : [7, 5]));
                        ctx.beginPath();
                        ctx.moveTo(a.x, a.y);
                        ctx.lineTo(b.x, b.y);
                        ctx.stroke();
                        drawArrowHead(a, b, blocked ? "#ff3b58" : color, blocked ? 1.2 : 1.0);
                    }
                    ctx.setLineDash([]);
                }

                if (mission.mode === "SPIN_360" && projected.length) {
                    const p = projected[0];
                    const blocked = Boolean(collisionReport?.blocked);
                    ctx.strokeStyle = blocked ? "#ff3b58" : color;
                    ctx.lineWidth = blocked ? 5 : 3;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, 15, 0, Math.PI * 2);
                    ctx.stroke();
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, 9, -Math.PI * 0.15, Math.PI * 1.6);
                    ctx.stroke();
                }

                projected.forEach((p, pointIndex) => {
                    const selectedPoint =
                        missionIndex === state.activeMission && pointIndex === state.selectedPoint;
                    ctx.fillStyle = color;
                    ctx.strokeStyle = selectedPoint ? "#ffffff" : "#202020";
                    ctx.lineWidth = selectedPoint ? 3 : 1;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, selectedPoint ? 7 : 5, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.stroke();
                    ctx.fillStyle = color;
                    ctx.font = "11px sans-serif";
                    ctx.fillText(String(pointIndex + 1), p.x + 8, p.y - 7);
                });
            }
        }
    }

    function loadBackground(meta) {
        const url = imageUrl(meta);
        if (!url) return;
        const image = new Image();
        image.onload = () => {
            state.background = image;
            canvas.width = image.naturalWidth;
            canvas.height = image.naturalHeight;
            draw();
        };
        image.src = url;
    }

    function ingestExecution(message) {
        const raw = message?.route_editor;
        const meta = Array.isArray(raw) ? raw[0] : raw;
        if (!meta?.projection || !meta?.plan) return;
        state.metadata = meta;
        state.projection = meta.projection;
        state.collisionStale = false;
        const perspective = meta.projection?.perspective_panel;
        if (perspective) {
            state.orbitYaw = Number(perspective.default_yaw_deg ?? -35) * Math.PI / 180;
            state.orbitPitch = Number(perspective.default_pitch_deg ?? -18) * Math.PI / 180;
            state.orbitZoom = Number(perspective.default_zoom ?? 1);
        }
        const cleanPlan = clone(meta.plan);
        delete cleanPlan.route_plan_dirty;
        setPlan(cleanPlan, true);
        state.collisionStale = false;
        updateToolbar();
        loadBackground(meta.editor_base_preview || meta.preview);
    }

    canvas.addEventListener("pointerdown", (event) => {
        if (!state.projection || !validPlan(state.plan)) return;
        const xy = eventCoordinates(event);
        if (!xy) return;
        const perspective = perspectivePanel();
        if (perspective && insideRect(perspective.plot_rect_px, xy.x, xy.y)) {
            state.orbitDragging = true;
            state.orbitLast = xy;
            canvas.setPointerCapture?.(event.pointerId);
            canvas.style.cursor = "grabbing";
            return;
        }
        const panel = panelAt(xy.x, xy.y);
        if (!panel) return;
        const mission = activeMission();
        if (!mission) return;

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
        const base =
            points[points.length - 1] ||
            defaultPoint(state.projection);
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
        if (state.orbitDragging && state.orbitLast) {
            const dx = xy.x - state.orbitLast.x;
            const dy = xy.y - state.orbitLast.y;
            state.orbitYaw += dx * 0.008;
            state.orbitPitch = Math.max(-1.35, Math.min(1.35, state.orbitPitch + dy * 0.008));
            state.orbitLast = xy;
            draw();
            return;
        }
        if (!state.dragging || state.selectedPoint == null) return;
        const panel = panelAt(xy.x, xy.y);
        if (!panel) return;
        const mission = activeMission();
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
        if (!state.dragging) return;
        state.dragging = false;
        state.dragHistoryPushed = false;
        state.orbitDragging = false;
        state.orbitLast = null;
        canvas.style.cursor = "crosshair";
        canvas.releasePointerCapture?.(event.pointerId);
    };
    canvas.addEventListener("pointerup", stopDrag);
    canvas.addEventListener("pointercancel", stopDrag);

    canvas.addEventListener("wheel", (event) => {
        if (!state.projection) return;
        const xy = eventCoordinates(event);
        const perspective = perspectivePanel();
        if (!xy || !perspective || !insideRect(perspective.plot_rect_px, xy.x, xy.y)) return;
        event.preventDefault();
        const factor = Math.exp(-event.deltaY * 0.0015);
        state.orbitZoom = Math.max(0.25, Math.min(5.0, state.orbitZoom * factor));
        draw();
    }, { passive: false });

    droneSelect.addEventListener("change", () => {
        state.activeMission = Number(droneSelect.value) || 0;
        state.selectedPoint = null;
        updateToolbar();
        draw();
    });

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

    resetScene.addEventListener("click", () => {
        state.history = [];
        state.plan = null;
        state.projection = null;
        state.metadata = null;
        state.selectedPoint = null;
        state.collisionStale = true;
        routeWidget.value = "";
        routeWidget.callback?.("");
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        status.textContent = "Rota descartada · execute o node para gerar a semente da cena atual";
        status.style.color = "#ffdc5a";
        selected.textContent = "";
        node.graph?.setDirtyCanvas?.(true, true);
        updateToolbar();
    });

    chainCallback(node, "onExecuted", function (message) {
        ingestExecution(message);
    });

    // Restore the serialized route immediately when a workflow is reopened.
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

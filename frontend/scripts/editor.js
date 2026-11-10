import { saveProject } from "./api.js";
import {
  contains,
  duplicateNode,
  findLocation,
  insertNode,
  moveNode,
  removeNode,
  sectionIdFor,
} from "./content-tree.js";

const clone = (value) => structuredClone(value);
const makeId = () => crypto.randomUUID();
const DROP_CLASSES = ["drop-before", "drop-after", "drop-inside"];
const SECTION_EDGE = 16;
const TYPE_LABELS = {
  section: "Секция",
  heading: "Заголовок",
  paragraph: "Текст",
  button: "Кнопка",
  eyebrow: "Надзаголовок",
};

function makeNode(type) {
  const defaults = {
    section: { background: "#f7f6f2", padding: "76px 9%", layout: "content" },
    heading: { text: "Новый заголовок", level: 2, color: "#202b2b", font_size: 36 },
    paragraph: { text: "Добавьте описание вашего проекта.", color: "#596361", font_size: 17 },
    button: { text: "Подробнее", background: "#263b38", color: "#ffffff" },
  };
  return { id: makeId(), type, props: defaults[type], children: [] };
}

function layerLabel(node) {
  const name = TYPE_LABELS[node.type] || String(node.type || "Элемент");
  const text = node.props && typeof node.props.text === "string"
    ? node.props.text.replace(/\s+/g, " ").trim()
    : "";
  if (!text) return name;
  return `${name} · ${text.length > 28 ? `${text.slice(0, 28)}…` : text}`;
}

function safeColor(value, fallback) {
  return /^#[0-9a-f]{3,8}$/i.test(String(value || "")) ? value : fallback;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function mountVisualEditor(host, sourceProject, pageId, onSaved, onBack) {
  let project = clone(sourceProject);
  let page = project.pages.find((item) => item.id === pageId) || project.pages.find((item) => item.is_home);
  if (!page) return;
  let selectedId = null;
  let viewport = "desktop";
  let libraryTab = "elements";
  let history = [clone(page.content.nodes)];
  let historyIndex = 0;
  let gesture = null;
  let dropIntent = null;
  let suppressClick = false;

  host.replaceChildren();
  host.hidden = false;
  const shell = element("section", "visual-editor");
  const toolbar = element("div", "editor-toolbar");
  const back = element("button", "button button-quiet", "← К проекту");
  back.type = "button";
  back.addEventListener("click", onBack);
  const title = element("div", "editor-page-title", page.title);
  const actions = element("div", "editor-toolbar-actions");
  const undo = element("button", "button button-secondary button-small", "↶");
  const redo = element("button", "button button-secondary button-small", "↷");
  const save = element("button", "button button-primary", "Сохранить");
  [undo, redo, save].forEach((button) => button.type = "button");
  actions.append(undo, redo, save);
  toolbar.append(back, title, actions);

  const workspace = element("div", "editor-workspace");
  const library = element("aside", "editor-library");
  const tabs = element("div", "editor-panel-tabs");
  const elementsTab = element("button", "editor-panel-tab is-active", "Элементы");
  const layersTab = element("button", "editor-panel-tab", "Слои");
  [elementsTab, layersTab].forEach((button) => button.type = "button");
  tabs.append(elementsTab, layersTab);
  const addSection = element("button", "editor-add-item", "＋ Секция");
  const addHeading = element("button", "editor-add-item", "＋ Заголовок");
  const addParagraph = element("button", "editor-add-item", "＋ Текст");
  const addButton = element("button", "editor-add-item", "＋ Кнопка");
  const elementButtons = [addSection, addHeading, addParagraph, addButton];
  elementButtons.forEach((button) => button.type = "button");
  const hint = element("p", "editor-hint", "Секция добавляется в корень страницы. Заголовок, текст и кнопка попадают в секцию. Порядок можно менять перетаскиванием на холсте.");
  const layersHost = element("div");
  layersHost.hidden = true;
  layersHost.style.width = "100%";
  library.append(tabs, addSection, addHeading, addParagraph, addButton, hint, layersHost);

  const stage = element("main", "editor-stage");
  const viewportBar = element("div", "editor-viewport-bar");
  const viewportButtons = {};
  [["desktop", "Монитор"], ["tablet", "Планшет"], ["mobile", "Телефон"]].forEach(([key, label]) => {
    const button = element("button", "button button-small button-quiet", label);
    button.type = "button";
    button.addEventListener("click", () => { viewport = key; render(); });
    viewportButtons[key] = button;
    viewportBar.append(button);
  });
  const canvasFrame = element("div", "editor-canvas-frame");
  const canvas = element("div", "editor-canvas");
  canvasFrame.append(canvas);
  stage.append(viewportBar, canvasFrame);

  const inspector = element("aside", "editor-inspector");
  inspector.append(element("div", "editor-panel-title", "СВОЙСТВА"));
  const inspectorBody = element("div", "editor-inspector-body", "Выберите элемент на холсте или в слоях");
  inspector.append(inspectorBody);
  workspace.append(library, stage, inspector);
  shell.append(toolbar, workspace);
  host.append(shell);

  function findNode(nodes, id) {
    for (const node of nodes) {
      if (node.id === id) return node;
      const found = findNode(node.children || [], id);
      if (found) return found;
    }
    return null;
  }

  function siblingsOf(nodes, parentId) {
    if (parentId === null) return Array.isArray(nodes) ? nodes : [];
    const parent = findNode(nodes, parentId);
    return parent && Array.isArray(parent.children) ? parent.children : [];
  }

  function record() {
    history = history.slice(0, historyIndex + 1);
    history.push(clone(page.content.nodes));
    historyIndex = history.length - 1;
    render();
  }

  function commitTree(next) {
    if (next === page.content.nodes) return false;
    page.content.nodes = next;
    record();
    return true;
  }

  function drawNode(node) {
    let view;
    const props = node.props || {};
    if (node.type === "section") {
      view = element("section", "site-section");
      view.style.backgroundColor = safeColor(props.background, "#f7f6f2");
      view.style.padding = /^([0-9.]+(px|rem|%|vh)\s*){1,4}$/.test(props.padding || "") ? props.padding : "64px 8%";
      (node.children || []).forEach((child) => view.append(drawNode(child)));
    } else if (node.type === "heading") {
      view = element(`h${[1, 2, 3].includes(Number(props.level)) ? Number(props.level) : 2}`, "site-heading", props.text || "");
      view.style.color = safeColor(props.color, "#202b2b");
      view.style.fontSize = `${Math.min(88, Math.max(14, Number(props.font_size) || 36))}px`;
    } else if (node.type === "paragraph" || node.type === "eyebrow") {
      view = element(node.type === "eyebrow" ? "div" : "p", node.type === "eyebrow" ? "site-eyebrow" : "site-paragraph", props.text || "");
      view.style.color = safeColor(props.color, node.type === "eyebrow" ? "#65736e" : "#596361");
      if (node.type === "paragraph") view.style.fontSize = `${Math.min(36, Math.max(12, Number(props.font_size) || 17))}px`;
    } else if (node.type === "button") {
      view = element("span", "site-button", props.text || "Кнопка");
      view.style.backgroundColor = safeColor(props.background, "#263b38");
      view.style.color = safeColor(props.color, "#ffffff");
    } else {
      view = element("div", "site-unknown", `Неизвестный элемент: ${node.type}`);
    }
    view.dataset.nodeId = node.id;
    view.classList.toggle("is-selected", node.id === selectedId);
    return view;
  }

  function structureActions(nodeId, compact) {
    const location = findLocation(page.content.nodes, nodeId);
    const siblings = location ? siblingsOf(page.content.nodes, location.parentId) : [];
    const index = location ? location.index : 0;
    const missing = !location;
    const specs = [
      ["К родителю", "↖", () => selectParent(nodeId), missing || location.parentId === null, false],
      ["Поднять", "↑", () => moveStep(nodeId, -1), missing || index <= 0, false],
      ["Опустить", "↓", () => moveStep(nodeId, 1), missing || index >= siblings.length - 1, false],
      ["Дублировать", "⧉", () => copyNode(nodeId), missing, false],
      ["Удалить", "×", () => deleteNode(nodeId), missing, true],
    ];
    const wrap = element("div", compact ? "editor-layer-actions" : "");
    if (compact) wrap.style.flexShrink = "0";
    else {
      wrap.style.display = "flex";
      wrap.style.flexWrap = "wrap";
      wrap.style.gap = "4px";
    }
    specs.forEach(([title, symbol, onClick, disabled, danger]) => {
      const button = element(
        "button",
        compact ? "" : `button button-small ${danger ? "button-danger-ghost" : "button-quiet"}`,
        compact ? symbol : title,
      );
      button.type = "button";
      button.title = title;
      button.setAttribute("aria-label", title);
      button.disabled = disabled;
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        onClick();
      });
      wrap.append(button);
    });
    return wrap;
  }

  function selectParent(nodeId) {
    const location = findLocation(page.content.nodes, nodeId);
    if (!location || location.parentId === null) return;
    selectedId = location.parentId;
    render();
  }

  function moveStep(nodeId, delta) {
    const location = findLocation(page.content.nodes, nodeId);
    if (!location) return;
    const nextIndex = location.index + delta;
    const siblings = siblingsOf(page.content.nodes, location.parentId);
    if (nextIndex < 0 || nextIndex >= siblings.length) return;
    commitTree(moveNode(page.content.nodes, nodeId, location.parentId, nextIndex));
  }

  function copyNode(nodeId) {
    const location = findLocation(page.content.nodes, nodeId);
    if (!location) return;
    const next = duplicateNode(page.content.nodes, nodeId, makeId);
    if (next === page.content.nodes) return;
    const copy = siblingsOf(next, location.parentId)[location.index + 1];
    page.content.nodes = next;
    if (copy) selectedId = copy.id;
    record();
  }

  function deleteNode(nodeId) {
    const nodes = page.content.nodes;
    const location = findLocation(nodes, nodeId);
    if (!location) return;
    const selectionLost = Boolean(selectedId && contains(nodes, nodeId, selectedId));
    const next = removeNode(nodes, nodeId);
    if (next === nodes) return;
    page.content.nodes = next;
    if (selectionLost) {
      const siblings = siblingsOf(next, location.parentId);
      const neighbor = siblings[location.index] || siblings[location.index - 1];
      selectedId = neighbor ? neighbor.id : location.parentId;
    }
    record();
  }

  function add(type) {
    if (type === "section") {
      const node = makeNode("section");
      const next = insertNode(page.content.nodes, null, page.content.nodes.length, node);
      if (next === page.content.nodes) return;
      page.content.nodes = next;
      selectedId = node.id;
      record();
      return;
    }
    let nodes = page.content.nodes;
    let parentId = sectionIdFor(nodes, selectedId);
    if (parentId === null) {
      const section = makeNode("section");
      nodes = insertNode(nodes, null, nodes.length, section);
      parentId = section.id;
    }
    const node = makeNode(type);
    const next = insertNode(nodes, parentId, siblingsOf(nodes, parentId).length, node);
    if (next === page.content.nodes) return;
    page.content.nodes = next;
    selectedId = node.id;
    record();
  }

  function renderInspector() {
    inspectorBody.replaceChildren();
    const node = selectedId ? findNode(page.content.nodes, selectedId) : null;
    if (!node) {
      inspectorBody.textContent = "Выберите элемент на холсте или в слоях";
      return;
    }
    inspectorBody.append(element("div", "editor-selected-type", String(node.type || "").toUpperCase()));
    if (node.type === "section") {
      const label = element("label", "field-label", "Фон секции");
      const color = element("input", "text-field");
      color.type = "color";
      color.value = safeColor(node.props.background, "#f7f6f2");
      color.addEventListener("input", () => { node.props.background = color.value; renderCanvas(); });
      color.addEventListener("change", record);
      inspectorBody.append(label, color);
    } else {
      const label = element("label", "field-label", "Текст");
      const textInput = element("textarea", "text-field text-area");
      textInput.rows = 5;
      textInput.value = node.props.text || "";
      textInput.addEventListener("input", () => { node.props.text = textInput.value; renderCanvas(); });
      textInput.addEventListener("change", record);
      inspectorBody.append(label, textInput);
      if (node.type === "heading" || node.type === "paragraph") {
        const sizeLabel = element("label", "field-label", "Размер текста");
        const size = element("input", "text-field");
        size.type = "number";
        size.min = "12";
        size.max = node.type === "heading" ? "88" : "36";
        size.value = Number(node.props.font_size) || (node.type === "heading" ? 36 : 17);
        size.addEventListener("input", () => { node.props.font_size = Number(size.value); renderCanvas(); });
        size.addEventListener("change", record);
        const colorLabel = element("label", "field-label", "Цвет текста");
        const color = element("input", "text-field");
        color.type = "color";
        color.value = safeColor(node.props.color, "#202b2b");
        color.addEventListener("input", () => { node.props.color = color.value; renderCanvas(); });
        color.addEventListener("change", record);
        inspectorBody.append(sizeLabel, size, colorLabel, color);
      }
    }
    inspectorBody.append(element("div", "field-label", "Структура"));
    inspectorBody.append(structureActions(node.id, false));
  }

  function renderCanvas() {
    canvas.replaceChildren();
    canvas.classList.toggle("viewport-tablet", viewport === "tablet");
    canvas.classList.toggle("viewport-mobile", viewport === "mobile");
    canvas.classList.toggle("viewport-desktop", viewport === "desktop");
    page.content.nodes.forEach((node) => canvas.append(drawNode(node)));
  }

  function buildLayerList(nodes, root) {
    const list = element("ul", root ? "editor-layers" : "editor-layer-children");
    nodes.forEach((node) => {
      if (!node || typeof node !== "object") return;
      const item = element("li", "editor-layer");
      item.classList.toggle("is-selected", node.id === selectedId);
      const label = element("span", "", layerLabel(node));
      label.style.flex = "1";
      label.style.minWidth = "0";
      label.style.overflow = "hidden";
      label.style.textOverflow = "ellipsis";
      label.style.whiteSpace = "nowrap";
      item.append(label, structureActions(node.id, true));
      if (Array.isArray(node.children) && node.children.length) item.append(buildLayerList(node.children, false));
      item.addEventListener("click", (event) => {
        event.stopPropagation();
        if (event.target.closest(".editor-layer-actions")) return;
        selectedId = node.id;
        render();
      });
      list.append(item);
    });
    return list;
  }

  function renderLayers() {
    layersHost.replaceChildren();
    if (!page.content.nodes.length) {
      layersHost.append(element("p", "editor-hint", "На странице пока нет элементов."));
      return;
    }
    layersHost.append(buildLayerList(page.content.nodes, true));
  }

  function renderLibrary() {
    const showElements = libraryTab === "elements";
    elementsTab.classList.toggle("is-active", showElements);
    layersTab.classList.toggle("is-active", !showElements);
    elementsTab.setAttribute("aria-pressed", showElements ? "true" : "false");
    layersTab.setAttribute("aria-pressed", showElements ? "false" : "true");
    elementButtons.forEach((button) => { button.hidden = !showElements; });
    hint.hidden = !showElements;
    layersHost.hidden = showElements;
    renderLayers();
  }

  function render() {
    Object.entries(viewportButtons).forEach(([key, button]) => button.classList.toggle("is-active", key === viewport));
    undo.disabled = historyIndex <= 0;
    redo.disabled = historyIndex >= history.length - 1;
    renderCanvas();
    renderInspector();
    renderLibrary();
  }

  function selectNode(id) {
    selectedId = id;
    canvas.querySelectorAll("[data-node-id]").forEach((el) => {
      el.classList.toggle("is-selected", el.dataset.nodeId === id);
    });
    renderInspector();
    renderLayers();
  }

  function paintDrop(intent) {
    let target = null;
    canvas.querySelectorAll("[data-node-id]").forEach((el) => {
      el.classList.remove(...DROP_CLASSES);
      if (intent && el.dataset.nodeId === intent.targetId) target = el;
    });
    if (target) target.classList.add(`drop-${intent.mode}`);
  }

  // `index` is the node's position in the destination parent after removal.
  function placement(source, targetId, mode) {
    const targetLocation = findLocation(page.content.nodes, targetId);
    if (!targetLocation) return null;
    let index = targetLocation.index + (mode === "after" ? 1 : 0);
    if (source.parentId === targetLocation.parentId && source.index < index) index -= 1;
    return { targetId, mode, parentId: targetLocation.parentId, index };
  }

  // Gaps in a section belong to the section element, so snap them to a child
  // edge. An empty section uses drop-inside and appends the dragged node.
  function dropInsideSection(sectionEl, y, dragId) {
    const children = [...sectionEl.children].filter((child) => {
      const childId = child.dataset && child.dataset.nodeId;
      return childId && !contains(page.content.nodes, dragId, childId);
    });
    if (!children.length) return null;
    for (const child of children) {
      const box = child.getBoundingClientRect();
      if (y < box.top + box.height / 2) return { targetId: child.dataset.nodeId, mode: "before" };
    }
    return { targetId: children[children.length - 1].dataset.nodeId, mode: "after" };
  }

  function dropIntentFromPoint(x, y, dragId) {
    const top = document.elementFromPoint(x, y);
    const hovered = top && top.closest ? top.closest("[data-node-id]") : null;
    if (!hovered || !canvas.contains(hovered)) return null;
    const targetId = hovered.dataset.nodeId;
    if (!targetId || contains(page.content.nodes, dragId, targetId)) return null;
    const source = findLocation(page.content.nodes, dragId);
    if (!source) return null;
    const target = findNode(page.content.nodes, targetId);
    const rect = hovered.getBoundingClientRect();
    const offset = y - rect.top;
    const sectionBand = target && target.type === "section" && rect.height > SECTION_EDGE * 2;
    if (sectionBand && offset > SECTION_EDGE && rect.height - offset > SECTION_EDGE) {
      const nested = dropInsideSection(hovered, y, dragId);
      if (nested) return placement(source, nested.targetId, nested.mode);
      return {
        targetId,
        mode: "inside",
        parentId: targetId,
        index: siblingsOf(page.content.nodes, targetId).length,
      };
    }
    const mode = offset < rect.height / 2 ? "before" : "after";
    return placement(source, targetId, mode);
  }

  function clearGestureListeners() {
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", endGesture);
    window.removeEventListener("pointercancel", endGesture);
  }

  function onPointerDown(event) {
    if (event.button !== 0 || event.isPrimary === false || gesture) return;
    const source = event.target.closest("[data-node-id]");
    if (!source || !canvas.contains(source)) return;
    event.preventDefault();
    gesture = {
      id: source.dataset.nodeId,
      x: event.clientX,
      y: event.clientY,
      pointerId: event.pointerId,
      dragging: false,
    };
    dropIntent = null;
    selectNode(source.dataset.nodeId);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", endGesture);
    window.addEventListener("pointercancel", endGesture);
  }

  function onPointerMove(event) {
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    if (!gesture.dragging) {
      const dx = event.clientX - gesture.x;
      const dy = event.clientY - gesture.y;
      if (dx * dx + dy * dy < 25) return;
      gesture.dragging = true;
      window.getSelection()?.removeAllRanges();
    }
    event.preventDefault();
    dropIntent = dropIntentFromPoint(event.clientX, event.clientY, gesture.id);
    paintDrop(dropIntent);
  }

  function endGesture(event) {
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    clearGestureListeners();
    const active = gesture;
    const intent = dropIntent;
    gesture = null;
    dropIntent = null;
    paintDrop(null);
    if (!canvas.isConnected) return;
    if (!active.dragging) {
      selectedId = active.id;
      render();
      return;
    }
    suppressClick = true;
    window.setTimeout(() => { suppressClick = false; }, 250);
    if (!intent) return;
    const next = moveNode(page.content.nodes, active.id, intent.parentId, intent.index);
    if (next === page.content.nodes) return;
    page.content.nodes = next;
    selectedId = active.id;
    record();
  }

  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("click", (event) => {
    if (suppressClick) return;
    const target = event.target.closest("[data-node-id]");
    if (!target || !canvas.contains(target)) return;
    selectedId = target.dataset.nodeId;
    render();
  });
  elementsTab.addEventListener("click", () => { libraryTab = "elements"; renderLibrary(); });
  layersTab.addEventListener("click", () => { libraryTab = "layers"; renderLibrary(); });
  addSection.addEventListener("click", () => add("section"));
  addHeading.addEventListener("click", () => add("heading"));
  addParagraph.addEventListener("click", () => add("paragraph"));
  addButton.addEventListener("click", () => add("button"));
  undo.addEventListener("click", () => {
    if (historyIndex <= 0) return;
    historyIndex -= 1;
    page.content.nodes = clone(history[historyIndex]);
    render();
  });
  redo.addEventListener("click", () => {
    if (historyIndex >= history.length - 1) return;
    historyIndex += 1;
    page.content.nodes = clone(history[historyIndex]);
    render();
  });
  save.addEventListener("click", async () => {
    save.disabled = true;
    try {
      const result = await saveProject(project);
      project = result.project;
      page = project.pages.find((item) => item.id === pageId);
      onSaved(project);
      save.textContent = "Сохранено";
      window.setTimeout(() => { save.textContent = "Сохранить"; save.disabled = false; }, 1200);
    } catch (error) {
      save.disabled = false;
      save.textContent = "Ошибка сохранения";
      console.error("Visual editor save failed:", error);
      window.alert(error.message);
    }
  });
  render();
}

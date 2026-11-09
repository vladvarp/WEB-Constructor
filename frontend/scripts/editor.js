import { saveProject } from "./api.js";

const clone = (value) => structuredClone(value);
const makeId = () => crypto.randomUUID();

function makeNode(type) {
  const defaults = {
    heading: { text: "Новый заголовок", level: 2, color: "#202b2b", font_size: 36 },
    paragraph: { text: "Добавьте описание вашего проекта.", color: "#596361", font_size: 17 },
    button: { text: "Подробнее", background: "#263b38", color: "#ffffff" },
  };
  return { id: makeId(), type, props: defaults[type], children: [] };
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
  let history = [clone(page.content.nodes)];
  let historyIndex = 0;

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
  library.append(element("div", "editor-panel-title", "ЭЛЕМЕНТЫ"));
  const addHeading = element("button", "editor-add-item", "＋ Заголовок");
  const addParagraph = element("button", "editor-add-item", "＋ Текст");
  const addButton = element("button", "editor-add-item", "＋ Кнопка");
  [addHeading, addParagraph, addButton].forEach((button) => button.type = "button");
  library.append(addHeading, addParagraph, addButton);
  library.append(element("p", "editor-hint", "Добавляйте элементы на страницу, затем выбирайте их прямо на холсте."));

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
  const inspectorBody = element("div", "editor-inspector-body", "Выберите элемент на холсте");
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

  function record() {
    history = history.slice(0, historyIndex + 1);
    history.push(clone(page.content.nodes));
    historyIndex = history.length - 1;
    render();
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
      view = element(`h${[1,2,3].includes(Number(props.level)) ? Number(props.level) : 2}`, "site-heading", props.text || "");
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

  function renderInspector() {
    inspectorBody.replaceChildren();
    const node = selectedId ? findNode(page.content.nodes, selectedId) : null;
    if (!node) {
      inspectorBody.textContent = "Выберите элемент на холсте";
      return;
    }
    inspectorBody.append(element("div", "editor-selected-type", node.type.toUpperCase()));
    if (node.type === "section") {
      const label = element("label", "field-label", "Фон секции");
      const color = element("input", "text-field");
      color.type = "color";
      color.value = safeColor(node.props.background, "#f7f6f2");
      color.addEventListener("input", () => { node.props.background = color.value; renderCanvas(); });
      color.addEventListener("change", record);
      inspectorBody.append(label, color);
      return;
    }
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

  function renderCanvas() {
    canvas.replaceChildren();
    canvas.classList.toggle("viewport-tablet", viewport === "tablet");
    canvas.classList.toggle("viewport-mobile", viewport === "mobile");
    canvas.classList.toggle("viewport-desktop", viewport === "desktop");
    page.content.nodes.forEach((node) => canvas.append(drawNode(node)));
    renderInspector();
  }

  function render() {
    Object.entries(viewportButtons).forEach(([key, button]) => button.classList.toggle("is-active", key === viewport));
    undo.disabled = historyIndex <= 0;
    redo.disabled = historyIndex >= history.length - 1;
    renderCanvas();
  }

  canvas.addEventListener("click", (event) => {
    const target = event.target.closest("[data-node-id]");
    if (!target || !canvas.contains(target)) return;
    selectedId = target.dataset.nodeId;
    render();
  });
  function add(type) {
    const node = makeNode(type);
    page.content.nodes.push(node);
    selectedId = node.id;
    record();
  }
  addHeading.addEventListener("click", () => add("heading"));
  addParagraph.addEventListener("click", () => add("paragraph"));
  addButton.addEventListener("click", () => add("button"));
  undo.addEventListener("click", () => {
    if (historyIndex > 0) { historyIndex -= 1; page.content.nodes = clone(history[historyIndex]); selectedId = null; render(); }
  });
  redo.addEventListener("click", () => {
    if (historyIndex < history.length - 1) { historyIndex += 1; page.content.nodes = clone(history[historyIndex]); selectedId = null; render(); }
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

export function setBackendStatus(online, message) {
  const indicator = document.querySelector("#backend-indicator");
  const status = document.querySelector("#backend-status");
  const serverState = document.querySelector("#server-state");
  indicator?.classList.toggle("is-online", online);
  indicator?.classList.toggle("is-offline", !online);
  if (status) status.textContent = message;
  if (serverState) serverState.textContent = online ? "Работает" : "Недоступен";
}

export function setModuleCount(count) {
  const target = document.querySelector("#module-count");
  if (target) target.textContent = String(count);
}

export function setProjectCount(count) {
  const target = document.querySelector("#project-count");
  if (target) target.textContent = String(count);
}

export function showToast(message, isError = false) {
  const toast = document.querySelector("#toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.toggle("is-error", isError);
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => toast.classList.remove("is-visible"), 3200);
}

export function renderProjectCards(projects, onOpen) {
  const list = document.querySelector("#project-list");
  if (!list) return;
  list.replaceChildren();

  if (!projects.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    const title = document.createElement("h2");
    title.textContent = "Пока нет проектов";
    const description = document.createElement("p");
    description.textContent = "Создай первый проект — здесь появится его карточка.";
    const action = document.createElement("button");
    action.className = "button button-primary";
    action.type = "button";
    action.textContent = "Создать проект";
    action.addEventListener("click", () => document.querySelector("#create-project-button")?.click());
    empty.append(title, description, action);
    list.append(empty);
    return;
  }

  for (const projectData of projects) {
    const card = document.createElement("article");
    card.className = "project-card";
    const main = document.createElement("div");
    main.className = "project-card-main";
    const title = document.createElement("h2");
    title.textContent = projectData.project.name;
    const subtitle = document.createElement("p");
    subtitle.textContent = projectData.site.title;
    const meta = document.createElement("span");
    meta.className = "project-card-meta";
    meta.textContent = `${projectData.pages.length} ${projectData.pages.length === 1 ? "страница" : "страниц"} · Изменён ${new Date(projectData.project.updated_at).toLocaleDateString("ru-RU")}`;
    main.append(title, subtitle, meta);
    const open = document.createElement("button");
    open.className = "button button-secondary";
    open.type = "button";
    open.textContent = "Открыть";
    open.addEventListener("click", () => onOpen(projectData.project.id));
    card.append(main, open);
    list.append(card);
  }
}

export function renderPages(pages, handlers = {}) {
  const list = document.querySelector("#page-list");
  if (!list) return;
  list.replaceChildren();

  pages.forEach((page, index) => {
    const row = document.createElement("article");
    row.className = "page-row";
    const details = document.createElement("div");
    details.className = "page-row-details";
    const title = document.createElement("strong");
    title.textContent = page.title;
    const slug = document.createElement("span");
    slug.textContent = `/${page.slug === "index" ? "" : page.slug}`;
    details.append(title, slug);
    row.append(details);

    if (page.is_home) {
      const home = document.createElement("span");
      home.className = "page-home-label";
      home.textContent = "Главная";
      row.append(home);
    }

    const actions = document.createElement("div");
    actions.className = "page-row-actions";
    const addAction = (label, titleText, callback, className = "button-quiet") => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `button button-small ${className}`;
      button.textContent = label;
      button.title = titleText;
      button.addEventListener("click", callback);
      actions.append(button);
    };
    addAction("↑", "Переместить выше", () => handlers.onMove?.(page.id, -1), "button-quiet");
    actions.lastElementChild.disabled = index === 0;
    addAction("↓", "Переместить ниже", () => handlers.onMove?.(page.id, 1), "button-quiet");
    actions.lastElementChild.disabled = index === pages.length - 1;
    addAction("Редактор", "Открыть страницу в визуальном редакторе", () => handlers.onOpenEditor?.(page.id), "button-secondary");
    addAction("Изменить", "Изменить название и адрес", () => handlers.onEdit?.(page.id), "button-secondary");
    if (!page.is_home) {
      addAction("Сделать главной", "Назначить главной", () => handlers.onSetHome?.(page.id), "button-quiet");
    }
    addAction("Удалить", "Удалить страницу", () => handlers.onDelete?.(page.id), "button-danger-ghost");
    row.append(actions);
    if (index === 0) row.classList.add("is-first-page");
    if (index === pages.length - 1) row.classList.add("is-last-page");
    list.append(row);
  });
}

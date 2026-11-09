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
  showToast.timeoutId = window.setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 3200);
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
    action.addEventListener("click", () => {
      document.querySelector("#create-project-button")?.click();
    });
    empty.append(title, description, action);
    list.append(empty);
    return;
  }

  for (const document of projects) {
    const card = document.createElement("article");
    card.className = "project-card";
    const main = document.createElement("div");
    main.className = "project-card-main";
    const title = document.createElement("h2");
    title.textContent = document.project.name;
    const subtitle = document.createElement("p");
    subtitle.textContent = document.site.title;
    const meta = document.createElement("span");
    meta.className = "project-card-meta";
    meta.textContent = `${document.pages.length} ${document.pages.length === 1 ? "страница" : "страниц"} · Изменён ${new Date(document.project.updated_at).toLocaleDateString("ru-RU")}`;
    main.append(title, subtitle, meta);
    const open = document.createElement("button");
    open.className = "button button-secondary";
    open.type = "button";
    open.textContent = "Открыть";
    open.addEventListener("click", () => onOpen(document.project.id));
    card.append(main, open);
    list.append(card);
  }
}

export function renderPages(pages) {
  const list = document.querySelector("#page-list");
  if (!list) return;
  list.replaceChildren();
  for (const page of pages) {
    const row = document.createElement("div");
    row.className = "page-row";
    const title = document.createElement("strong");
    title.textContent = page.title;
    const slug = document.createElement("span");
    slug.textContent = `/${page.slug === "index" ? "" : page.slug}`;
    row.append(title, slug);
    if (page.is_home) {
      const home = document.createElement("span");
      home.className = "page-home-label";
      home.textContent = "Главная";
      row.append(home);
    }
    list.append(row);
  }
}

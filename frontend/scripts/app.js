import {
  createPage,
  createProject,
  deletePage,
  deleteProject,
  getHealth,
  getModules,
  getProject,
  getProjects,
  reorderPages,
  saveProject,
  setHomePage,
  updatePage,
} from "./api.js";
import {
  renderPages,
  renderProjectCards,
  setBackendStatus,
  setModuleCount,
  setProjectCount,
  showToast,
} from "./ui.js";

let activeProject = null;
let projectCache = [];

const projectsView = document.querySelector("#projects-view");
const projectView = document.querySelector("#project-view");
const createDialog = document.querySelector("#create-project-dialog");
const createForm = document.querySelector("#create-project-form");
const createPageDialog = document.querySelector("#create-page-dialog");
const createPageForm = document.querySelector("#create-page-form");

const transliteration = {
  а:"a", б:"b", в:"v", г:"g", д:"d", е:"e", ё:"e", ж:"zh", з:"z", и:"i",
  й:"y", к:"k", л:"l", м:"m", н:"n", о:"o", п:"p", р:"r", с:"s", т:"t",
  у:"u", ф:"f", х:"h", ц:"ts", ч:"ch", ш:"sh", щ:"sch", ы:"y", э:"e",
  ю:"yu", я:"ya", ъ:"", ь:"",
};

function slugify(value) {
  return [...value.toLowerCase()]
    .map((char) => transliteration[char] ?? char)
    .join("")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120);
}

async function refreshProjects() {
  const result = await getProjects();
  projectCache = result.projects;
  renderProjectCards(projectCache, openProject);
  setProjectCount(projectCache.length);
}

function showProjects() {
  activeProject = null;
  projectView.hidden = true;
  projectsView.hidden = false;
}

function renderActivePages() {
  if (!activeProject) return;
  renderPages(activeProject.pages, {
    onEdit: handleEditPage,
    onSetHome: handleSetHomePage,
    onDelete: handleDeletePage,
    onMove: handleMovePage,
  });
}

async function openProject(projectId) {
  try {
    const result = await getProject(projectId);
    activeProject = result.project;
    projectsView.hidden = true;
    projectView.hidden = false;
    document.querySelector("#project-heading").textContent = activeProject.project.name;
    document.querySelector("#project-name").value = activeProject.project.name;
    document.querySelector("#site-title").value = activeProject.site.title;
    document.querySelector("#site-description").value = activeProject.site.description;
    document.querySelector("#site-language").value = activeProject.site.language;
    document.querySelector("#project-meta").textContent =
      `Создан: ${new Date(activeProject.project.created_at).toLocaleString("ru-RU")} · ID: ${activeProject.project.id}`;
    renderActivePages();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function reloadActiveProject() {
  if (!activeProject) return;
  const result = await getProject(activeProject.project.id);
  activeProject = result.project;
  document.querySelector("#project-heading").textContent = activeProject.project.name;
  renderActivePages();
  await refreshProjects();
}

async function handleCreateProject(event) {
  event.preventDefault();
  const input = document.querySelector("#new-project-name");
  const name = input.value.trim();
  if (!name) {
    input.focus();
    return;
  }

  try {
    const result = await createProject(name);
    createDialog.close();
    createForm.reset();
    await refreshProjects();
    await openProject(result.project.project.id);
    showToast("Проект создан");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function handleSaveProject() {
  if (!activeProject) return;
  const updated = structuredClone(activeProject);
  updated.project.name = document.querySelector("#project-name").value.trim();
  updated.site.title = document.querySelector("#site-title").value.trim();
  updated.site.description = document.querySelector("#site-description").value;
  updated.site.language = document.querySelector("#site-language").value;

  try {
    const result = await saveProject(updated);
    activeProject = result.project;
    document.querySelector("#project-heading").textContent = activeProject.project.name;
    await refreshProjects();
    showToast("Изменения сохранены");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function handleDeleteProject() {
  if (!activeProject) return;
  if (!window.confirm(`Удалить проект «${activeProject.project.name}» без возможности восстановления?`)) return;

  try {
    await deleteProject(activeProject.project.id);
    showProjects();
    await refreshProjects();
    showToast("Проект удалён");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function handleCreatePage(event) {
  event.preventDefault();
  if (!activeProject) return;
  const titleInput = document.querySelector("#new-page-title");
  const slugInput = document.querySelector("#new-page-slug");
  const title = titleInput.value.trim();
  const slug = slugInput.value.trim().toLowerCase();
  if (!title || !slug) return;

  try {
    const result = await createPage(activeProject.project.id, title, slug);
    activeProject = result.project;
    createPageDialog.close();
    createPageForm.reset();
    renderActivePages();
    await refreshProjects();
    showToast("Страница создана");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function handleEditPage(pageId) {
  const page = activeProject?.pages.find((item) => item.id === pageId);
  if (!page) return;
  const title = window.prompt("Название страницы:", page.title);
  if (title === null) return;
  const slug = window.prompt("Адрес страницы (латиница, цифры и дефис):", page.slug);
  if (slug === null) return;
  try {
    const result = await updatePage(activeProject.project.id, pageId, title, slug);
    activeProject = result.project;
    renderActivePages();
    await refreshProjects();
    showToast("Страница обновлена");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function handleSetHomePage(pageId) {
  try {
    const result = await setHomePage(activeProject.project.id, pageId);
    activeProject = result.project;
    renderActivePages();
    await refreshProjects();
    showToast("Главная страница изменена");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function handleDeletePage(pageId) {
  const page = activeProject?.pages.find((item) => item.id === pageId);
  if (!page || !window.confirm(`Удалить страницу «${page.title}»?`)) return;
  try {
    const result = await deletePage(activeProject.project.id, pageId);
    activeProject = result.project;
    renderActivePages();
    await refreshProjects();
    showToast("Страница удалена");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function handleMovePage(pageId, offset) {
  if (!activeProject) return;
  const pages = [...activeProject.pages];
  const index = pages.findIndex((page) => page.id === pageId);
  const target = index + offset;
  if (index < 0 || target < 0 || target >= pages.length) return;
  [pages[index], pages[target]] = [pages[target], pages[index]];
  try {
    const result = await reorderPages(activeProject.project.id, pages.map((page) => page.id));
    activeProject = result.project;
    renderActivePages();
    await refreshProjects();
  } catch (error) {
    showToast(error.message, true);
  }
}

document.querySelector("#create-project-button").addEventListener("click", () => {
  createDialog.showModal();
  document.querySelector("#new-project-name").focus();
});
document.querySelector("#close-create-dialog").addEventListener("click", () => createDialog.close());
document.querySelector("#cancel-create-project").addEventListener("click", () => createDialog.close());
createForm.addEventListener("submit", handleCreateProject);
document.querySelector("#back-to-projects").addEventListener("click", showProjects);
document.querySelector("#save-project-button").addEventListener("click", handleSaveProject);
document.querySelector("#delete-project-button").addEventListener("click", handleDeleteProject);

document.querySelector("#add-page-button").addEventListener("click", () => {
  createPageDialog.showModal();
  document.querySelector("#new-page-title").focus();
});
document.querySelector("#close-create-page-dialog").addEventListener("click", () => createPageDialog.close());
document.querySelector("#cancel-create-page").addEventListener("click", () => createPageDialog.close());
createPageForm.addEventListener("submit", handleCreatePage);
document.querySelector("#new-page-title").addEventListener("input", (event) => {
  const slug = document.querySelector("#new-page-slug");
  if (!slug.dataset.edited) slug.value = slugify(event.target.value);
});
document.querySelector("#new-page-slug").addEventListener("input", (event) => {
  event.target.dataset.edited = "true";
});
createPageDialog.addEventListener("close", () => {
  createPageForm.reset();
  document.querySelector("#new-page-slug").dataset.edited = "";
});

async function initialize() {
  try {
    const [health, moduleResult] = await Promise.all([getHealth(), getModules()]);
    setBackendStatus(health.status === "ok", "Система готова");
    setModuleCount(moduleResult.modules.length);
    await refreshProjects();
  } catch (error) {
    console.error("Application initialization failed:", error);
    setBackendStatus(false, "Нет соединения");
    setModuleCount("Ошибка");
    showToast(error.message, true);
    document.querySelector("#project-list").textContent = "Не удалось загрузить проекты.";
  }
}

initialize();

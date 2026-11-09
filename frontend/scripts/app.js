import {
  createProject,
  deleteProject,
  getHealth,
  getModules,
  getProject,
  getProjects,
  saveProject,
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
    renderPages(activeProject.pages);
  } catch (error) {
    showToast(error.message, true);
  }
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
  if (!window.confirm(`Удалить проект «${activeProject.project.name}» без возможности восстановления?`)) {
    return;
  }

  try {
    await deleteProject(activeProject.project.id);
    showProjects();
    await refreshProjects();
    showToast("Проект удалён");
  } catch (error) {
    showToast(error.message, true);
  }
}

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

initialize();

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
let selectedMenuId = null;

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
  renderNavigation(activeProject.menus || [], activeProject.pages, selectedMenuId);
}

async function openProject(projectId) {
  try {
    const result = await getProject(projectId);
    activeProject = result.project;
    selectedMenuId = activeProject.menus?.[0]?.id || null;
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


async function navigationRequest(path, options = {}) {
  const response = await fetch(path,{...options,headers:{"Content-Type":"application/json",Accept:"application/json"}});
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Ошибка API: ${response.status}`);
  return data;
}
function navPath(projectId) { return `/api/projects/${encodeURIComponent(projectId)}/menus`; }
function renderNavigation(menus,pages,selectedId) {
  const select=document.querySelector("#navigation-menu-select"), editor=document.querySelector("#navigation-editor");
  const list=document.querySelector("#navigation-item-list"), pageSelect=document.querySelector("#navigation-page-target");
  const parentSelect=document.querySelector("#navigation-parent-target"); select.replaceChildren();
  menus.forEach(menu=>{const o=document.createElement("option");o.value=menu.id;o.textContent=menu.name;select.append(o);});
  if(!menus.length){editor.hidden=true;return;}
  select.value=selectedId||menus[0].id; const menu=menus.find(m=>m.id===select.value)||menus[0]; editor.hidden=false;
  document.querySelector("#navigation-menu-name").value=menu.name;
  document.querySelector("#navigation-menu-location").value=menu.location;
  pageSelect.replaceChildren(); pages.forEach(p=>{const o=document.createElement("option");o.value=p.id;o.textContent=p.title;pageSelect.append(o);});
  parentSelect.replaceChildren();const root=document.createElement("option");root.value="";root.textContent="Верхний уровень";parentSelect.append(root);list.replaceChildren();
  const draw=(items,depth=0)=>items.forEach((item,index)=>{
    const row=document.createElement("div");row.className="navigation-item-row";row.style.marginLeft=`${depth*20}px`;
    const label=document.createElement("span");label.textContent=`${item.label} · ${item.kind==="page"?(pages.find(p=>p.id===item.page_id)?.title||"Страница"):item.url}`;
    const actions=document.createElement("div");actions.className="navigation-item-actions";
    const btn=(txt,title,fn,disabled=false)=>{const b=document.createElement("button");b.type="button";b.className="button button-quiet button-small";b.textContent=txt;b.title=title;b.disabled=disabled;b.addEventListener("click",fn);actions.append(b);};
    btn("↑","Выше",()=>moveNavigation(item.id,-1),index===0);btn("↓","Ниже",()=>moveNavigation(item.id,1),index===items.length-1);
    btn("Изм.","Изменить название",()=>editNavigationItem(item.id));btn("×","Удалить",()=>removeNavigationItem(item.id));
    row.append(label,actions);list.append(row);
    const parent=document.createElement("option");parent.value=item.id;parent.textContent=`${"　".repeat(depth)}${item.label}`;parentSelect.append(parent);draw(item.children||[],depth+1);
  }); draw(menu.items);
}
function findNav(items,id){for(const item of items){if(item.id===id)return item;const found=findNav(item.children||[],id);if(found)return found;}return null;}
function removeNav(items,id){return items.filter(i=>i.id!==id).map(i=>({...i,children:removeNav(i.children||[],id)}));}
function moveNav(items,id,offset){const index=items.findIndex(i=>i.id===id);if(index>=0){const target=index+offset;if(target>=0&&target<items.length)[items[index],items[target]]=[items[target],items[index]];return true;}return items.some(i=>moveNav(i.children||[],id,offset));}
async function saveNav(menu){
  try{const r=await navigationRequest(`${navPath(activeProject.project.id)}/${menu.id}`,{method:"PUT",body:JSON.stringify({name:menu.name,location:menu.location,items:menu.items})});activeProject=r.project;renderActivePages();await refreshProjects();showToast("Меню сохранено");}
  catch(e){showToast(e.message,true);}
}
async function removeNavigationItem(id){const menu=activeProject.menus.find(m=>m.id===selectedMenuId);if(menu)await saveNav({...menu,items:removeNav(menu.items,id)});}
async function moveNavigation(id,offset){const menu=activeProject.menus.find(m=>m.id===selectedMenuId);if(!menu)return;const items=structuredClone(menu.items);if(moveNav(items,id,offset))await saveNav({...menu,items});}
async function editNavigationItem(id){const menu=activeProject.menus.find(m=>m.id===selectedMenuId),item=menu&&findNav(menu.items,id);if(!item)return;const label=prompt("Название пункта:",item.label);if(label===null||!label.trim())return;const items=structuredClone(menu.items);findNav(items,id).label=label.trim();await saveNav({...menu,items});}
async function addNavigationMenu(){const name=prompt("Название меню:","Основное меню");if(name===null||!name.trim())return;try{const r=await navigationRequest(navPath(activeProject.project.id),{method:"POST",body:JSON.stringify({name:name.trim(),location:"header"})});activeProject=r.project;selectedMenuId=activeProject.menus.at(-1).id;renderActivePages();await refreshProjects();showToast("Меню создано");}catch(e){showToast(e.message,true);}}
async function saveNavigationSettings(){const menu=activeProject.menus.find(m=>m.id===selectedMenuId);if(menu)await saveNav({...menu,name:document.querySelector("#navigation-menu-name").value.trim(),location:document.querySelector("#navigation-menu-location").value});}
async function addNavigationItem(event){event.preventDefault();const menu=activeProject.menus.find(m=>m.id===selectedMenuId);if(!menu)return;const kind=document.querySelector("#navigation-item-kind").value;
  const item={id:crypto.randomUUID(),label:document.querySelector("#navigation-item-label").value.trim(),kind,page_id:kind==="page"?document.querySelector("#navigation-page-target").value:null,url:kind==="external"?document.querySelector("#navigation-url-target").value.trim():null,children:[]};
  const items=structuredClone(menu.items),parentId=document.querySelector("#navigation-parent-target").value;if(parentId){const parent=findNav(items,parentId);if(!parent)return;parent.children.push(item);}else items.push(item);
  await saveNav({...menu,items});document.querySelector("#navigation-item-form").reset();document.querySelector("#navigation-page-target-wrap").hidden=false;document.querySelector("#navigation-url-target-wrap").hidden=true;}
async function deleteNavigationMenuHandler(){const menu=activeProject.menus.find(m=>m.id===selectedMenuId);if(!menu||!confirm(`Удалить меню «${menu.name}»?`))return;try{const r=await navigationRequest(`${navPath(activeProject.project.id)}/${menu.id}`,{method:"DELETE"});activeProject=r.project;selectedMenuId=activeProject.menus[0]?.id||null;renderActivePages();await refreshProjects();showToast("Меню удалено");}catch(e){showToast(e.message,true);}}

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

document.querySelector("#add-navigation-menu").addEventListener("click",addNavigationMenu);
document.querySelector("#navigation-menu-select").addEventListener("change",e=>{selectedMenuId=e.target.value;renderActivePages();});
document.querySelector("#navigation-item-kind").addEventListener("change",e=>{const ext=e.target.value==="external";document.querySelector("#navigation-page-target-wrap").hidden=ext;document.querySelector("#navigation-url-target-wrap").hidden=!ext;});
document.querySelector("#navigation-item-form").addEventListener("submit",addNavigationItem);
document.querySelector("#save-navigation-menu").addEventListener("click",saveNavigationSettings);
document.querySelector("#delete-navigation-menu").addEventListener("click",deleteNavigationMenuHandler);

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

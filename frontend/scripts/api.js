async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let message = `Ошибка API: ${response.status}`;
    try {
      const payload = await response.json();
      if (payload.detail) message = payload.detail;
    } catch {
      // Keep the HTTP status when the server did not return JSON.
    }
    throw new Error(message);
  }

  if (response.status === 204) return null;
  return response.json();
}

export const getHealth = () => request("/api/health");
export const getModules = () => request("/api/modules");
export const getProjects = () => request("/api/projects");
export const getProject = (id) => request(`/api/projects/${encodeURIComponent(id)}`);
export const createProject = (name) => request("/api/projects", {
  method: "POST",
  body: JSON.stringify({ name }),
});
export const saveProject = (project) => request(
  `/api/projects/${encodeURIComponent(project.project.id)}`,
  { method: "PUT", body: JSON.stringify({ project }) },
);
export const deleteProject = (id) => request(
  `/api/projects/${encodeURIComponent(id)}`,
  { method: "DELETE" },
);
const projectPagesPath = (projectId) => `/api/projects/${encodeURIComponent(projectId)}/pages`;
export const createPage = (projectId, title, slug) => request(projectPagesPath(projectId), {
  method: "POST", body: JSON.stringify({ title, slug }),
});
export const updatePage = (projectId, pageId, title, slug) => request(
  `${projectPagesPath(projectId)}/${encodeURIComponent(pageId)}`,
  { method: "PUT", body: JSON.stringify({ title, slug }) },
);
export const setHomePage = (projectId, pageId) => request(
  `${projectPagesPath(projectId)}/${encodeURIComponent(pageId)}/home`,
  { method: "POST" },
);
export const deletePage = (projectId, pageId) => request(
  `${projectPagesPath(projectId)}/${encodeURIComponent(pageId)}`,
  { method: "DELETE" },
);
export const reorderPages = (projectId, pageIds) => request(
  `${projectPagesPath(projectId)}/order`,
  { method: "PUT", body: JSON.stringify({ page_ids: pageIds }) },
);

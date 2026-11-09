async function request(path) {
  const response = await fetch(path, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
  return response.json();
}
export const getHealth = () => request("/api/health");
export const getModules = () => request("/api/modules");

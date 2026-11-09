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

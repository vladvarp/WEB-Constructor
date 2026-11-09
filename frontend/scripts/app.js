import { getHealth, getModules } from "./api.js";
import { setBackendStatus, setModuleCount } from "./ui.js";

async function initialize() {
  try {
    const [health, moduleResult] = await Promise.all([getHealth(), getModules()]);
    setBackendStatus(health.status === "ok", "Система готова");
    setModuleCount(moduleResult.modules.length);
  } catch (error) {
    console.error("Application initialization failed:", error);
    setBackendStatus(false, "Нет соединения");
    setModuleCount("Ошибка");
  }
}
initialize();

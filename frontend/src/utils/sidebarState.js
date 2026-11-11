export const defaultSidebarOpen = true;

export function activeSidebarPage(page) {
  return page || "sessions";
}

export function activeSidebarRoute(pathname) {
  if (pathname === "/dashboard") return "dashboard";
  if (pathname === "/scenarios") return "scenarios";
  return "sessions";
}

export function drawerState(open, action) {
  if (action === "open") return true;
  if (action === "close" || action === "navigate" || action === "backdrop")
    return false;
  return open;
}

export function closeAfterNavigation(onClose, windowRef = globalThis.window) {
  if (windowRef?.matchMedia?.("(max-width: 850px)").matches) onClose();
}

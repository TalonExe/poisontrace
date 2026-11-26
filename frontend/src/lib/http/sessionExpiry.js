let generation = 0;

export function advanceSessionGeneration() {
  generation += 1;
}

export function sessionGeneration() {
  return generation;
}

export function notifySessionExpiry(response, startedGeneration) {
  if (response.status === 401 && startedGeneration === generation && globalThis.window?.dispatchEvent) {
    window.dispatchEvent(new Event('poisontrace-session-ended'));
  }
}

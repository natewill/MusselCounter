const DEFAULT_API_BASE = 'http://127.0.0.1:8000';
const API_BASE_SESSION_KEY = 'mussel_api_base';

let cachedApiBase: string | null = null;

function normalizeApiBase(apiBase: string): string {
  return apiBase.trim().replace(/\/+$/, '');
}

function readBrowserConfiguredApiBase(): string | null {
  if (typeof window === 'undefined') return null;

  const params = new URLSearchParams(window.location.search);
  const apiBaseFromParam = params.get('apiBase');
  const backendHost = params.get('backendHost');
  const backendPort = params.get('backendPort');

  let configured: string | null = null;
  if (apiBaseFromParam) {
    configured = normalizeApiBase(apiBaseFromParam);
  } else if (backendHost && backendPort && /^\d+$/.test(backendPort)) {
    configured = normalizeApiBase(`http://${backendHost}:${backendPort}`);
  }

  if (configured) {
    window.sessionStorage.setItem(API_BASE_SESSION_KEY, configured);
    return configured;
  }

  const stored = window.sessionStorage.getItem(API_BASE_SESSION_KEY);
  return stored ? normalizeApiBase(stored) : null;
}

export function getApiBase(): string {
  if (cachedApiBase) return cachedApiBase;

  const browserConfigured = readBrowserConfiguredApiBase();
  if (browserConfigured) {
    cachedApiBase = browserConfigured;
    return cachedApiBase;
  }

  const envApiBase = process.env.NEXT_PUBLIC_API_BASE;
  if (envApiBase) {
    cachedApiBase = normalizeApiBase(envApiBase);
    return cachedApiBase;
  }

  const envBackendPort = process.env.NEXT_PUBLIC_BACKEND_PORT;
  if (envBackendPort && /^\d+$/.test(envBackendPort)) {
    cachedApiBase = normalizeApiBase(`http://127.0.0.1:${envBackendPort}`);
    return cachedApiBase;
  }

  cachedApiBase = DEFAULT_API_BASE;
  return cachedApiBase;
}

export function getUploadUrl(storedPath?: string | null): string | null {
  if (!storedPath) return null;

  // Support run-scoped upload paths (e.g. .../data/uploads/run_12/image.jpg)
  // and older flat paths by always generating a URL relative to /uploads.
  const normalized = storedPath.replace(/\\/g, '/');
  const uploadsMarker = '/uploads/';
  const markerIndex = normalized.lastIndexOf(uploadsMarker);

  let relativePath: string;
  if (markerIndex >= 0) {
    relativePath = normalized.slice(markerIndex + uploadsMarker.length);
  } else {
    const fileName = normalized.split('/').pop();
    if (!fileName) return null;
    relativePath = fileName;
  }

  return `${getApiBase()}/uploads/${relativePath}`;
}

const API_BASE = "http://127.0.0.1:8000";

export async function pingBackend() {
  const res = await fetch(`${API_BASE}/`);
  return res.json();
}
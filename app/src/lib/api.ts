const API_BASE = "http://127.0.0.1:8765";

export async function fetchJSON(path: string, init?: RequestInit): Promise<unknown> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(text || `HTTP ${res.status}`);
  }
  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return res.json();
  }
  return res.text();
}

export async function postJSON(path: string, body: unknown): Promise<unknown> {
  return fetchJSON(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

interface ApiWrapper<T> {
  ok: boolean;
  data: T;
  message?: string;
}

export async function fetchData<T>(path: string, init?: RequestInit): Promise<T> {
  const wrapper = (await fetchJSON(path, init)) as ApiWrapper<T>;
  if (!wrapper.ok) {
    throw new Error(wrapper.message || "API error");
  }
  return wrapper.data;
}

export async function postData<T>(path: string, body: unknown): Promise<T> {
  const wrapper = (await postJSON(path, body)) as ApiWrapper<T>;
  if (!wrapper.ok) {
    throw new Error(wrapper.message || "API error");
  }
  return wrapper.data;
}

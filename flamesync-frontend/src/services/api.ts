// src/services/api.ts

const BASE_URL = 'http://127.0.0.1:8000/api';

async function request(endpoint: string, init?: RequestInit) {
  const response = await fetch(`${BASE_URL}${endpoint}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null) as {
      detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>;
    } | null;
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((item) => `${item.loc?.join('.') ?? 'input'}: ${item.msg ?? 'invalid value'}`).join('; ')
      : body?.detail;
    throw new Error(detail || `API Error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export const api = {
  get: async (endpoint: string) => request(endpoint),
  
  post: async (endpoint: string, data: unknown) => request(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    }),
};
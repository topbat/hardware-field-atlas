import { useEffect, useState } from 'react';
import { onlineDemo } from './deployment.js';

const workspaceKey = 'hardware-atlas.workspace.v1';
let sessionToken;

function workspaceToken() {
  if (sessionToken) return sessionToken;
  try {
    const saved = localStorage.getItem(workspaceKey);
    if (saved && /^[a-f0-9]{64}$/.test(saved)) {
      sessionToken = saved;
      return saved;
    }
  } catch {
    // Private browser settings can disallow persistent storage.
  }

  sessionToken = Array.from(crypto.getRandomValues(new Uint8Array(32)), (byte) => (
    byte.toString(16).padStart(2, '0')
  )).join('');
  try {
    localStorage.setItem(workspaceKey, sessionToken);
  } catch {
    // Keep the workspace available for this tab's session.
  }
  return sessionToken;
}

export async function request(path, { body, method = 'GET', signal, workspace = false } = {}) {
  if (onlineDemo) {
    const { demoRequest } = await import('./demo-api.js');
    return demoRequest(path, { method, body, signal });
  }
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (workspace) headers.Authorization = `Bearer ${workspaceToken()}`;
  const response = await fetch(`/api${path}`, {
    method,
    headers,
    signal,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return null;
  const value = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 404) throw new Error('没有找到这条档案。');
    if (response.status === 429) throw new Error('请求过多，请稍后再试。');
    if (typeof value?.detail === 'string' && value.detail.length < 260) throw new Error(value.detail);
    throw new Error(response.status === 422 ? '请检查提交内容。' : '服务暂时无法连接，请稍后再试。');
  }
  if (value === null) throw new Error('服务返回了无法读取的响应。');
  return value;
}

export function useResource(path, { workspace = false } = {}) {
  const [result, setResult] = useState({ path: null, value: null, error: null });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!path) return undefined;
    const controller = new AbortController();
    request(path, { signal: controller.signal, workspace })
      .then((value) => {
        if (!controller.signal.aborted) setResult({ path, value, error: null });
      })
      .catch((error) => {
        if (!controller.signal.aborted) setResult({ path, value: null, error: error.message });
      });
    return () => controller.abort();
  }, [path, workspace, attempt]);
  return {
    value: result.path === path ? result.value : null,
    error: result.path === path ? result.error : null,
    loading: Boolean(path && result.path !== path),
    retry: () => {
      setResult({ path: null, value: null, error: null });
      setAttempt((value) => value + 1);
    },
  };
}

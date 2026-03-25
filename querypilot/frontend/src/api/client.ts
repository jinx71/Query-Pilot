import axios from 'axios';
import type {
  ChatData,
  Envelope,
  SchemaData,
  SessionData,
} from '../types';

// Same-origin '/api' — Vite proxies this to the FastAPI backend in dev, and in
// production the frontend is served behind the same host (or VITE_API_BASE).
const baseURL = import.meta.env.VITE_API_BASE ?? '';

const http = axios.create({ baseURL, timeout: 60_000 });

/** Unwrap the {success, data, message} envelope, throwing on failure. */
function unwrap<T>(env: Envelope<T>): T {
  if (!env.success || env.data === null) {
    throw new Error(env.message || 'Request failed');
  }
  return env.data;
}

/** Turn an axios error into a human-readable message for the UI. */
export function describeError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (err.code === 'ECONNABORTED') return 'The request timed out.';
    return err.message;
  }
  return err instanceof Error ? err.message : 'Unexpected error';
}

export async function createSession(): Promise<string> {
  const { data } = await http.post<Envelope<SessionData>>('/api/session');
  return unwrap(data).session_id;
}

export async function resetSession(sessionId: string): Promise<void> {
  await http.post<Envelope<SessionData>>(
    `/api/session/${encodeURIComponent(sessionId)}/reset`,
  );
}

export async function getSchema(): Promise<SchemaData> {
  const { data } = await http.get<Envelope<SchemaData>>('/api/schema');
  return unwrap(data);
}

export async function sendChat(
  message: string,
  sessionId: string | null,
): Promise<ChatData> {
  const { data } = await http.post<Envelope<ChatData>>('/api/chat', {
    message,
    session_id: sessionId,
  });
  return unwrap(data);
}

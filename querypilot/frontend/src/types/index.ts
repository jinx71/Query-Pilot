// These types mirror the backend Pydantic models in app/models.py so the
// wire format stays in lockstep across the two languages.

export interface Envelope<T> {
  success: boolean;
  data: T | null;
  message: string;
}

/** One tool call the agent made: the SQL it ran and what came back. */
export interface QueryStep {
  purpose: string | null;
  sql: string;
  ok: boolean;
  error: string | null;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  truncated: boolean;
  elapsed_ms: number;
}

export interface ChatData {
  session_id: string;
  answer: string;
  steps: QueryStep[];
}

export interface SessionData {
  session_id: string;
}

export interface ColumnInfo {
  name: string;
  type: string;
  primary_key: boolean;
  nullable: boolean;
  references: string | null;
  sample_values: string[] | null;
}

export interface TableInfo {
  name: string;
  columns: ColumnInfo[];
}

export interface SchemaData {
  tables: TableInfo[];
}

/** UI-side chat message. Assistant turns carry the agent's query steps. */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  steps?: QueryStep[];
  error?: boolean;
}

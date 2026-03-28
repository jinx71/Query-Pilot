import { useCallback, useEffect, useRef, useState } from 'react';
import {
  createSession,
  describeError,
  resetSession,
  sendChat,
} from '../api/client';
import type { ChatMessage } from '../types';

let counter = 0;
const nextId = () => `m${Date.now()}-${counter++}`;

interface UseChat {
  messages: ChatMessage[];
  sending: boolean;
  sessionReady: boolean;
  send: (text: string) => Promise<void>;
  reset: () => Promise<void>;
}

/**
 * Owns the conversation: lazily creates a server-side session, sends messages
 * through the agent, and appends the assistant's answer plus its SQL steps.
 */
export function useChat(): UseChat {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const sessionId = useRef<string | null>(null);
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const id = await createSession();
        if (!cancelled) {
          sessionId.current = id;
          setSessionReady(true);
        }
      } catch {
        // The first chat call will transparently create a session as a
        // fallback, so a failure here is non-fatal.
        if (!cancelled) setSessionReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || sending) return;

      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'user', text: trimmed },
      ]);
      setSending(true);

      try {
        const data = await sendChat(trimmed, sessionId.current);
        sessionId.current = data.session_id;
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: 'assistant',
            text: data.answer,
            steps: data.steps,
          },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: 'assistant',
            text: describeError(err),
            error: true,
          },
        ]);
      } finally {
        setSending(false);
      }
    },
    [sending],
  );

  const reset = useCallback(async () => {
    const id = sessionId.current;
    setMessages([]);
    if (id) {
      try {
        await resetSession(id);
      } catch {
        // If the reset call fails we still clear the UI; a new session will be
        // minted on the next message.
        sessionId.current = null;
      }
    }
  }, []);

  return { messages, sending, sessionReady, send, reset };
}

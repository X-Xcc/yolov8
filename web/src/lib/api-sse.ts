import { getWorkspaceApiUrl } from './api-config';

type SseCallback = (data: unknown) => void;

const SSE_EVENT_TYPES = ['cameras', 'alerts', 'system_metrics', 'audit_logs', 'camera_stats'] as const;

const sseSubscribers = new Map<string, Set<SseCallback>>();
let sseEventSource: EventSource | null = null;
let sseReconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectDelay = 1000;
const MAX_RECONNECT_DELAY = 60000;

function ensureSseConnection(): void {
  if (sseEventSource && sseEventSource.readyState !== EventSource.CLOSED) return;
  if (sseReconnectTimer) {
    clearTimeout(sseReconnectTimer);
    sseReconnectTimer = null;
  }

  const eventSource = new EventSource(getWorkspaceApiUrl('/api/sse/stream'));

  for (const eventType of SSE_EVENT_TYPES) {
    eventSource.addEventListener(eventType, (event: MessageEvent) => {
      const subscribers = sseSubscribers.get(eventType);
      if (!subscribers || subscribers.size === 0) return;

      let data: unknown;
      try {
        data = JSON.parse(event.data);
        if (typeof data === 'string') data = JSON.parse(data);
      } catch {
        return;
      }

      subscribers.forEach(callback => {
        try {
          callback(data);
        } catch {
          // ignore subscriber errors to keep SSE fanout alive
        }
      });
    });
  }

  eventSource.onopen = () => {
    reconnectDelay = 1000;
  };

  eventSource.onerror = () => {
    eventSource.close();
    sseEventSource = null;
    if (sseSubscribers.size > 0) {
      const delay = reconnectDelay;
      sseReconnectTimer = setTimeout(() => {
        ensureSseConnection();
      }, delay);
      reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
    }
  };

  sseEventSource = eventSource;
}

export function subscribeSse(eventType: string, callback: SseCallback): () => void {
  if (!sseSubscribers.has(eventType)) sseSubscribers.set(eventType, new Set());
  sseSubscribers.get(eventType)!.add(callback);
  ensureSseConnection();

  return () => {
    const subscribers = sseSubscribers.get(eventType);
    if (subscribers) {
      subscribers.delete(callback);
      if (subscribers.size === 0) sseSubscribers.delete(eventType);
    }

    if (sseSubscribers.size === 0 && sseEventSource) {
      sseEventSource.close();
      sseEventSource = null;
    }
  };
}

/**
 * LOCUS MODIFICATION 3 — audit interceptor
 *
 * Wraps OpenClaw's tool call lifecycle with audit logging.
 * Every tool dispatch is recorded with timing, input, and output metadata.
 *
 * Audit events are:
 *   1. Logged to console (always)
 *   2. Sent via non-blocking POST to ${LOCUS_API_URL}/api/v1/internal/audit/openclaw
 *
 * If the FastAPI backend is unreachable, the event is written to console only.
 * Audit logging NEVER blocks or fails a tool call.
 */

// LOCUS MODIFICATION 3 — audit interceptor
const LOCUS_API_URL = process.env.LOCUS_API_URL || "http://localhost:3000";
const LOCUS_SERVICE_TOKEN = process.env.LOCUS_SERVICE_TOKEN || "";

export interface AuditEvent {
  event_type: "tool_call_start" | "tool_call_end";
  tool_name: string;
  timestamp: string;
  input_payload?: unknown;
  response_status?: string;
  duration_ms?: number;
  error?: string;
}

// LOCUS MODIFICATION 3 — audit interceptor
function fireAuditEvent(event: AuditEvent): void {
  // Always log to console
  console.log(`[LOCUS:AUDIT] ${event.event_type}`, JSON.stringify(event));

  // Non-blocking POST to FastAPI — fire and forget
  try {
    fetch(`${LOCUS_API_URL}/api/v1/internal/audit/openclaw`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${LOCUS_SERVICE_TOKEN}`,
      },
      body: JSON.stringify(event),
      signal: AbortSignal.timeout(5000),
    }).catch((err: Error) => {
      // LOCUS MODIFICATION 3 — audit interceptor: never block on failure
      console.warn(`[LOCUS:AUDIT] Failed to send audit event: ${err.message}`);
    });
  } catch {
    // LOCUS MODIFICATION 3 — audit interceptor: swallow all errors
  }
}

// LOCUS MODIFICATION 3 — audit interceptor
export function auditBeforeToolCall(toolName: string, inputPayload?: unknown): void {
  fireAuditEvent({
    event_type: "tool_call_start",
    tool_name: toolName,
    timestamp: new Date().toISOString(),
    input_payload: inputPayload,
  });
}

// LOCUS MODIFICATION 3 — audit interceptor
export function auditAfterToolCall(
  toolName: string,
  startTime: number,
  status: string,
  error?: string
): void {
  const durationMs = Date.now() - startTime;
  fireAuditEvent({
    event_type: "tool_call_end",
    tool_name: toolName,
    timestamp: new Date().toISOString(),
    response_status: status,
    duration_ms: durationMs,
    error,
  });
}

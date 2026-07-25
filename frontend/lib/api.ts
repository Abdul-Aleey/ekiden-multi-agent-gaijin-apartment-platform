import type { ApplicantProfile, InquiryEmail, SearchPreferences } from "./types";

// `??` (not `||`) deliberately: an explicitly-empty NEXT_PUBLIC_API_URL means
// "same origin, use relative paths" (the single-Cloud-Run-service deploy
// shape) and must NOT fall back to the localhost default.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface SSEEvent {
  event: string;
  data: any;
}

/**
 * POST /api/chat and yield parsed SSE events as they arrive. EventSource
 * can't POST a body, so we parse the text/event-stream response manually.
 */
export async function* streamChat(
  message: string,
  profile: ApplicantProfile,
  priorPrefs: SearchPreferences | null,
  lang: "en" | "ja" = "en",
  signal?: AbortSignal
): AsyncGenerator<SSEEvent> {
  const resp = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, profile, prior_prefs: priorPrefs, lang }),
    signal,
  });

  if (!resp.ok || !resp.body) {
    throw new Error(`Chat request failed: ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // sse-starlette separates events with "\r\n\r\n", not "\n\n" — match either.
    const chunks = buffer.split(/\r?\n\r?\n/);
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const lines = chunk.split(/\r?\n/);
      let eventName = "message";
      let dataStr = "";
      for (const line of lines) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
      }
      if (dataStr) {
        try {
          yield { event: eventName, data: JSON.parse(dataStr) };
        } catch {
          // ignore unparseable keep-alive chunks
        }
      }
    }
  }
}

export async function askFollowup(
  listingId: string,
  question: string,
  lang: "en" | "ja" = "en"
): Promise<string> {
  const resp = await fetch(`${API_URL}/api/listing/${listingId}/followup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ listing_id: listingId, question, lang }),
  });
  if (!resp.ok) throw new Error(`Follow-up request failed: ${resp.status}`);
  const data = await resp.json();
  return data.answer;
}

export async function generateInquiry(
  listingId: string,
  profile: ApplicantProfile
): Promise<InquiryEmail> {
  const resp = await fetch(`${API_URL}/api/listing/${listingId}/inquiry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ listing_id: listingId, profile }),
  });
  if (!resp.ok) throw new Error(`Inquiry request failed: ${resp.status}`);
  return resp.json();
}

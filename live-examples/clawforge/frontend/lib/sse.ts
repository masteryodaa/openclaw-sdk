export type SSEHandler = (event: string, data: unknown) => void;

export async function streamSSE(
  url: string,
  body: Record<string, unknown>,
  onEvent: SSEHandler,
  signal?: AbortSignal
): Promise<void> {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8200";
  const res = await fetch(`${API_URL}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok) {
    throw new Error(`SSE request failed: ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "message";
    for (const line of lines) {
      const trimmed = line.replace(/\r$/, ""); // strip trailing \r from \r\n
      if (trimmed === "") {
        // Blank line = end of event, reset for next
        currentEvent = "message";
      } else if (trimmed.startsWith("event:")) {
        currentEvent = trimmed.slice(6).trim();
      } else if (trimmed.startsWith("data:")) {
        const dataStr = trimmed.slice(5).trim();
        try {
          const data = JSON.parse(dataStr);
          onEvent(currentEvent, data);
        } catch {
          onEvent(currentEvent, dataStr);
        }
      }
      // Skip comment lines (starting with :)
    }
  }
}

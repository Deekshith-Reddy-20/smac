import { getApiBase } from "./index";

export function diag(stage: string, detail: Record<string, unknown> = {}) {
  void fetch(`${getApiBase()}/api/debug/trace`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      stage,
      source: typeof detail.source === "string" ? detail.source : undefined,
      ok: typeof detail.ok === "boolean" ? detail.ok : undefined,
      detail,
    }),
  }).catch(() => undefined);
}

export async function pollDiagCommand(): Promise<Record<string, unknown> | null> {
  try {
    const response = await fetch(`${getApiBase()}/api/debug/command`);
    const data = (await response.json()) as { command?: Record<string, unknown> | null };
    return data.command ?? null;
  } catch {
    return null;
  }
}

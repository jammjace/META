import type { IdentificationResult } from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000").replace(/\/+$/, "");

export async function createIdentification(front: File, back: File): Promise<IdentificationResult> {
  const form = new FormData();
  form.append("front", front);
  form.append("back", back);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/identifications`, { method: "POST", body: form });
  } catch {
    throw new Error(`Could not reach the analysis server at ${API_BASE}.`);
  }
  if (!response.ok) {
    let message = `Identification failed (${response.status}).`;
    try {
      const body = await response.json() as { detail?: string };
      if (body.detail) message = body.detail;
    } catch { /* keep status message */ }
    throw new Error(message);
  }
  return response.json() as Promise<IdentificationResult>;
}

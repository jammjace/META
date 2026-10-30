import type { AnalysisResult, ComparisonResult } from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000").replace(/\/+$/, "");

export function apiUrl(path: string): string {
  return /^https?:\/\//.test(path) ? path : `${API_BASE}${path.startsWith("/") ? "" : "/"}${path}`;
}

async function responseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body = await response.json() as { detail?: string };
      if (body.detail) message = body.detail;
    } catch { /* retain status message */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export async function createAnalysis(photo: File): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("photo", photo);
  return responseJson(await fetch(`${API_BASE}/api/analyses`, { method: "POST", body: form }));
}

export async function getAnalysis(id: string): Promise<AnalysisResult> {
  return responseJson(await fetch(`${API_BASE}/api/analyses/${encodeURIComponent(id)}`, { cache: "no-store" }));
}

export async function createComparison(baseline: File, current: File): Promise<ComparisonResult> {
  const form = new FormData();
  form.append("baseline", baseline);
  form.append("current", current);
  return responseJson(await fetch(`${API_BASE}/api/comparisons`, { method: "POST", body: form }));
}

export async function getComparison(id: string): Promise<ComparisonResult> {
  return responseJson(await fetch(`${API_BASE}/api/comparisons/${encodeURIComponent(id)}`, { cache: "no-store" }));
}


"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { createComparison } from "@/lib/api";

const ALLOWED = new Set(["image/jpeg", "image/png", "image/webp"]);
const MAX = 12 * 1024 * 1024;

function PhotoPicker({ label, file, onFile }: { label: string; file: File | null; onFile: (file: File) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  useEffect(() => {
    if (!file) { setPreview(null); return; }
    const url = URL.createObjectURL(file); setPreview(url); return () => URL.revokeObjectURL(url);
  }, [file]);
  return <div className="compare-picker"><p className="eyebrow">{label}</p>
    <button type="button" className="dropzone compare-dropzone" onClick={() => input.current?.click()}>
      {preview ? <img src={preview} alt={`${label} preview`} /> : <><span className="upload-glyph">↑</span><strong>Choose photo</strong><small>JPEG, PNG or WebP</small></>}
    </button>
    <input ref={input} hidden type="file" accept="image/jpeg,image/png,image/webp" onChange={event => {
      const candidate = event.target.files?.[0];
      if (candidate && ALLOWED.has(candidate.type) && candidate.size <= MAX) onFile(candidate);
    }} />
  </div>;
}

export default function ComparePage() {
  const router = useRouter();
  const [baseline, setBaseline] = useState<File | null>(null);
  const [current, setCurrent] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function analyze() {
    if (!baseline || !current || busy) return;
    setBusy(true); setError(null);
    try { const result = await createComparison(baseline, current); router.push(`/comparisons/${result.comparison_id}`); }
    catch (cause) { setBusy(false); setError(cause instanceof Error ? cause.message : "Comparison failed."); }
  }
  return <main className="shell">
    <header className="masthead"><Link href="/" className="mark">FORM</Link><span>Progress comparison</span></header>
    <section className="compare-head"><p className="eyebrow">TWO-PHOTO ANALYSIS</p><h1>Then.<br />Now.</h1><p>Use two similarly framed back photos with comparable arm positions and lighting.</p></section>
    <section className="compare-upload-grid"><PhotoPicker label="01 · Baseline" file={baseline} onFile={setBaseline} /><PhotoPicker label="02 · Current" file={current} onFile={setCurrent} /></section>
    {error && <p className="error" role="alert">{error}</p>}
    <button className="primary" disabled={!baseline || !current || busy} onClick={analyze}>{busy ? "Comparing both photos…" : "Analyze progress"}<span>→</span></button>
  </main>;
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { createAnalysis } from "@/lib/api";

const ALLOWED = new Set(["image/jpeg", "image/png", "image/webp"]);
const MAX_BYTES = 12 * 1024 * 1024;

export default function UploadPage() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!file) { setPreview(null); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function choose(candidate?: File) {
    if (!candidate) return;
    if (!ALLOWED.has(candidate.type)) { setError("Choose a JPEG, PNG, or WebP image."); return; }
    if (candidate.size > MAX_BYTES) { setError("The photo must be 12 MB or smaller."); return; }
    setError(null);
    setFile(candidate);
  }

  async function analyze() {
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    try {
      const result = await createAnalysis(file);
      router.push(`/results/${result.analysis_id}`);
    } catch (cause) {
      setBusy(false);
      setError(cause instanceof Error ? cause.message : "Analysis failed.");
    }
  }

  return (
    <main className="shell">
      <header className="masthead"><span className="mark">FORM</span><span>Baseline 01</span></header>
      <section className="intro">
        <p className="eyebrow">POSE-GUIDED VISUAL ANALYSIS</p>
        <h1>See the structure<br />of your back.</h1>
        <p className="lede">Upload one clear upper-body back photo. We’ll map approximate muscle regions and produce concise visual observations.</p>
      </section>

      <section className="workspace">
        <button className={`dropzone ${preview ? "has-image" : ""}`} onClick={() => input.current?.click()} type="button">
          {preview ? <img src={preview} alt="Selected back photo preview" /> : <>
            <span className="upload-glyph">↑</span>
            <strong>Choose a back photo</strong>
            <small>JPEG, PNG or WebP · 12 MB max</small>
          </>}
        </button>
        <input ref={input} hidden type="file" accept="image/jpeg,image/png,image/webp" onChange={e => choose(e.target.files?.[0])} />

        <div className="brief">
          <span className="step">01</span><div><strong>Use a straight-on back view</strong><p>Keep both shoulders and hips visible. Even light and a neutral stance work best.</p></div>
          <span className="step">02</span><div><strong>One analysis request</strong><p>The baseline sends the whole image and all regions in one model call.</p></div>
          <span className="step">03</span><div><strong>Visual, not clinical</strong><p>Annotations are approximate and are not a measurement of muscle mass.</p></div>
        </div>
      </section>

      {error && <p className="error" role="alert">{error}</p>}
      <button className="primary" disabled={!file || busy} onClick={analyze}>
        {busy ? "Analyzing photo…" : "Analyze back photo"}<span>→</span>
      </button>
      <Link className="secondary home-compare-link" href="/compare">Compare two progress photos</Link>
    </main>
  );
}


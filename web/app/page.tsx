"use client";

import { useEffect, useRef, useState } from "react";
import { IdentificationView } from "@/components/identification-view";
import { createIdentification } from "@/lib/api";
import type { IdentificationResult } from "@/lib/types";

const ALLOWED = new Set(["image/jpeg", "image/png", "image/webp"]);
const MAX_BYTES = 12 * 1024 * 1024;

function PhotoPicker({ view, file, onFile, onError }: {
  view: "Front" | "Back";
  file: File | null;
  onFile: (file: File) => void;
  onError: (message: string) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  useEffect(() => {
    if (!file) { setPreview(null); return; }
    const url = URL.createObjectURL(file); setPreview(url); return () => URL.revokeObjectURL(url);
  }, [file]);
  function choose(candidate?: File) {
    if (!candidate) return;
    if (!ALLOWED.has(candidate.type)) return onError("Choose JPEG, PNG, or WebP photos.");
    if (candidate.size > MAX_BYTES) return onError("Each photo must be 12 MB or smaller.");
    onError(""); onFile(candidate);
  }
  return <article className="view-picker">
    <div className="picker-title"><span>{view === "Front" ? "01" : "02"}</span><div><strong>{view} view</strong><p>Upper body, neutral stance, shoulders and hips visible.</p></div></div>
    <button type="button" className="dropzone paired-dropzone" onClick={() => input.current?.click()}>
      {preview ? <img src={preview} alt={`${view} photo preview`} /> : <><span className="upload-glyph">↑</span><strong>Choose {view.toLowerCase()} photo</strong><small>JPEG, PNG or WebP</small></>}
    </button>
    <input ref={input} hidden type="file" accept="image/jpeg,image/png,image/webp" onChange={event => choose(event.target.files?.[0])} />
  </article>;
}

export default function HomePage() {
  const [front, setFront] = useState<File | null>(null);
  const [back, setBack] = useState<File | null>(null);
  const [result, setResult] = useState<IdentificationResult | null>(null);
  const [frontUrl, setFrontUrl] = useState("");
  const [backUrl, setBackUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function reset() {
    if (frontUrl) URL.revokeObjectURL(frontUrl);
    if (backUrl) URL.revokeObjectURL(backUrl);
    setResult(null); setFront(null); setBack(null); setFrontUrl(""); setBackUrl(""); setError("");
  }
  async function identify() {
    if (!front || !back || busy) return;
    setBusy(true); setError("");
    try {
      const response = await createIdentification(front, back);
      setFrontUrl(URL.createObjectURL(front));
      setBackUrl(URL.createObjectURL(back));
      setResult(response);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Identification failed.");
    } finally { setBusy(false); }
  }

  return <main className="shell">
    <header className="masthead"><span className="mark">FORM</span><span>Upper-body anatomy</span></header>
    {!result ? <>
      <section className="intro identification-intro">
        <p className="eyebrow">AI-ASSISTED MUSCLE IDENTIFICATION</p>
        <h1>Map what’s<br />visible.</h1>
        <p className="lede">Upload one front and one back upper-body photo. MediaPipe anchors approximate regions; Muse Spark identifies and describes only meaningfully locatable anatomy.</p>
      </section>
      <section className="paired-upload-grid">
        <PhotoPicker view="Front" file={front} onFile={setFront} onError={setError} />
        <PhotoPicker view="Back" file={back} onFile={setBack} onError={setError} />
      </section>
      <div className="privacy-note"><strong>Session only.</strong> Photos are processed for this request and are not written to application storage.</div>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="primary" disabled={!front || !back || busy} onClick={identify}>{busy ? "Identifying muscles…" : "Identify upper-body muscles"}<span>→</span></button>
    </> : <>
      <button className="secondary result-reset" onClick={reset}>Start a new session</button>
      <IdentificationView result={result} frontUrl={frontUrl} backUrl={backUrl} />
    </>}
  </main>;
}

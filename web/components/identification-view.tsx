"use client";

import { useMemo, useState } from "react";
import { AnnotatedPhoto, type DiagnosticLayers } from "./annotated-photo";
import { muscleStyle } from "@/lib/overlay.mjs";
import type { IdentificationResult, IdentifiedMuscle } from "@/lib/types";

export function IdentificationView({ result, frontUrl, backUrl }: {
  result: IdentificationResult; frontUrl: string; backUrl: string;
}) {
  const all = useMemo(() => [...result.front.muscles, ...result.back.muscles], [result]);
  const [selected, setSelected] = useState(all[0]?.name ?? "");
  const [layers, setLayers] = useState<DiagnosticLayers>({ template: true, muse: true, final: true });
  const selectedMuscle = all.find(muscle => muscle.name === selected);
  const toggleLayer = (layer: keyof DiagnosticLayers) =>
    setLayers(current => ({ ...current, [layer]: !current[layer] }));
  return <section className="identification-results">
    <div className="identification-heading">
      <p className="eyebrow">INTERACTIVE ANATOMY MAP</p>
      <h2>Visible upper-body muscles</h2>
      <p>Select a colored region or anatomical name. Deeper locations are explicitly marked as estimates.</p>
    </div>
    <div className="diagnostic-layer-controls" aria-label="Diagnostic annotation layers">
      <strong>Localization layers</strong>
      <button className="template-toggle" aria-pressed={layers.template} onClick={() => toggleLayer("template")}>
        <span />MediaPipe template
      </button>
      <button className="muse-toggle" aria-pressed={layers.muse} onClick={() => toggleLayer("muse")}>
        <span />Muse raw localization
      </button>
      <button className="final-toggle" aria-pressed={layers.final} onClick={() => toggleLayer("final")}>
        <span />Final outline
      </button>
    </div>
    <div className="identification-images">
      <AnnotatedPhoto side={result.front} sourceUrl={frontUrl} label="Front" selected={selected} onSelect={setSelected} layers={layers} />
      <AnnotatedPhoto side={result.back} sourceUrl={backUrl} label="Back" selected={selected} onSelect={setSelected} layers={layers} />
    </div>
    <div className="muscle-directory">
      {(["chest", "shoulders", "arms", "back", "core", "obliques", "spine"] as const).map(group => {
        const muscles = all.filter(muscle => muscle.group === group);
        if (!muscles.length) return null;
        const style = muscleStyle(group);
        return <section key={group} className="muscle-group-card">
          <h3><span style={{ background: style.fill }} />{group}</h3>
          {muscles.map((muscle: IdentifiedMuscle) => <button key={`${muscle.name}-${muscle.side}`} className={selected === muscle.name ? "selected" : ""} onClick={() => setSelected(muscle.name)}>
            <strong>{muscle.display_name}</strong>
            <small>{muscle.location_quality === "estimated_deep" ? "Estimated deeper location" : muscle.location_quality === "covered_surface" ? "Covered surface estimate" : "Visible surface anatomy"}</small>
          </button>)}
        </section>;
      })}
    </div>
    {selectedMuscle && <article className="selected-muscle-detail">
      <p className="eyebrow">SELECTED MUSCLE</p>
      <h3>{selectedMuscle.display_name}</h3>
      <p>{selectedMuscle.observation}</p>
      <span>{selectedMuscle.location_quality === "estimated_deep" ? "Approximate deeper anatomical location" : selectedMuscle.location_quality === "covered_surface" ? "Surface muscle with visually hidden boundaries" : "Visible surface muscle"}</span>
    </article>}
    <aside className="notice">{result.warnings.map(warning => <p key={warning}>{warning}</p>)}</aside>
  </section>;
}

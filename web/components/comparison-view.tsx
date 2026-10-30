"use client";

import { useState } from "react";
import { AnnotatedPhoto } from "./annotated-photo";
import type { ComparisonResult } from "@/lib/types";

const STATUS = { visible_progress: "Visible progress", no_clear_change: "No clear change", inconclusive: "Inconclusive" } as const;

export function ComparisonView({ result }: { result: ComparisonResult }) {
  const [selected, setSelected] = useState(result.muscle_progress[0]?.muscle ?? "");
  return <>
    <div className="comparison-images">
      <AnnotatedPhoto side={result.baseline} label="Before" selected={selected} onSelect={setSelected} />
      <AnnotatedPhoto side={result.current} label="Now" selected={selected} onSelect={setSelected} />
    </div>
    <section className="progress-report">
      {result.muscle_progress.map((item, index) => {
        const display = result.baseline.annotations.find(m => m.name === item.muscle)?.display_name ?? item.muscle;
        return <button key={item.muscle} className={selected === item.muscle ? "selected" : ""} onClick={() => setSelected(item.muscle)}>
          <span className="report-index">{String(index + 1).padStart(2, "0")}</span>
          <div><strong>{display}</strong><p>{item.observation}</p>{item.limitation && <small>{item.limitation}</small>}</div>
          <span className={`status status-${item.status}`}>{STATUS[item.status]}</span>
        </button>;
      })}
    </section>
  </>;
}

"use client";

import { useState } from "react";
import { apiUrl } from "@/lib/api";
import { muscleStyle, smoothClosedPath } from "@/lib/overlay.mjs";
import type { AnalysisResult } from "@/lib/types";

export function AnnotatedImage({ result }: { result: AnalysisResult }) {
  const [selected, setSelected] = useState(result.muscles[0]?.name ?? "");
  return <div className="annotated-wrap">
    <div className="image-stage">
      <img src={apiUrl(result.image.url)} alt="Analyzed upper-body back" />
      <svg viewBox={`0 0 ${result.image.width} ${result.image.height}`} aria-label="Approximate muscle annotations">
        {result.muscles.filter(m => m.visible).map((muscle) => {
          const style = muscleStyle(muscle.group);
          const anchor = {
            x: muscle.annotation.label_anchor.x * result.image.width,
            y: muscle.annotation.label_anchor.y * result.image.height,
          };
          const label = {
            x: muscle.annotation.label_position.x * result.image.width,
            y: muscle.annotation.label_position.y * result.image.height,
          };
          const isActive = selected === muscle.name;
          const textAnchor = label.x < result.image.width / 2 ? "start" : "end";
          const lineEndX = label.x + (textAnchor === "start" ? -10 : 10);
          return <g
            key={muscle.name}
            className={`muscle-overlay ${isActive ? "active" : ""}`}
            onClick={() => setSelected(muscle.name)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") setSelected(muscle.name);
            }}
            tabIndex={0}
            role="button"
            aria-label={`Show ${muscle.display_name} observation`}
          >
            <path
              d={smoothClosedPath(muscle.annotation.pixel_points)}
              style={{ fill: style.fill, stroke: style.stroke }}
            >
              <title>{muscle.display_name}: approximate anatomical region</title>
            </path>
            <line x1={anchor.x} y1={anchor.y} x2={lineEndX} y2={label.y} />
            <circle cx={anchor.x} cy={anchor.y} r={isActive ? 6 : 4} style={{ fill: style.stroke }} />
            <text x={label.x} y={label.y} textAnchor={textAnchor} dominantBaseline="middle">
              {muscle.display_name}
            </text>
          </g>;
        })}
      </svg>
    </div>
    <div className="observations">
      {result.muscles.map((muscle, index) => <button key={muscle.name} className={selected === muscle.name ? "selected" : ""} onClick={() => setSelected(muscle.name)}>
        <span>{String(index + 1).padStart(2, "0")}</span>
        <div><strong>{muscle.display_name}</strong><p>{muscle.observation}</p></div>
      </button>)}
    </div>
  </div>;
}


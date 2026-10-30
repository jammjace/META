"use client";

import { apiUrl } from "@/lib/api";
import { muscleStyle, smoothClosedPath } from "@/lib/overlay.mjs";
import type { ComparisonSide } from "@/lib/types";

export function AnnotatedPhoto({ side, label, selected, onSelect }: {
  side: ComparisonSide; label: string; selected: string; onSelect: (name: string) => void;
}) {
  return <article className="comparison-photo">
    <div className="photo-label"><strong>{label}</strong><span>{side.view} view</span></div>
    <div className="image-stage comparison-stage">
      <img src={apiUrl(side.image.url)} alt={`${label} upper-body photo`} />
      <svg viewBox={`0 0 ${side.image.width} ${side.image.height}`} aria-label={`${label} approximate muscle annotations`}>
        {side.annotations.filter(m => m.visible).map(muscle => {
          const style = muscleStyle(muscle.group);
          return <g key={muscle.name} className={`muscle-overlay ${selected === muscle.name ? "active" : ""}`}
            onClick={() => onSelect(muscle.name)} tabIndex={0} role="button" aria-label={`Select ${muscle.display_name}`}>
            <path d={smoothClosedPath(muscle.annotation.pixel_points)} style={{ fill: style.fill, stroke: style.stroke }}>
              <title>{muscle.display_name}: approximate anatomical region</title>
            </path>
          </g>;
        })}
      </svg>
    </div>
  </article>;
}

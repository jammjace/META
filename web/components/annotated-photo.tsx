"use client";

import { smoothClosedPath } from "@/lib/overlay.mjs";
import type { IdentificationSide } from "@/lib/types";

export type DiagnosticLayers = { template: boolean; muse: boolean; final: boolean };

export function AnnotatedPhoto({ side, label, sourceUrl, selected, onSelect, layers }: {
  side: IdentificationSide;
  label: string;
  sourceUrl: string;
  selected: string;
  onSelect: (name: string) => void;
  layers: DiagnosticLayers;
}) {
  return <article className="anatomy-photo">
    <div className="photo-label"><strong>{label}</strong><span>{side.view} view</span></div>
    <div className="image-stage anatomy-stage diagnostic-stage">
      <img src={sourceUrl} alt={`${label} upper-body photo`} />
      <svg viewBox={`0 0 ${side.image.width} ${side.image.height}`} aria-label={`${label} localization diagnostics`}>
        {side.muscles.filter(muscle => muscle.visible).map(muscle => {
          const active = selected === muscle.name;
          const anchor = {
            x: muscle.annotation.label_anchor.x * side.image.width,
            y: muscle.annotation.label_anchor.y * side.image.height,
          };
          const labelPoint = {
            x: muscle.annotation.label_position.x * side.image.width,
            y: muscle.annotation.label_position.y * side.image.height,
          };
          const box = muscle.grounding_box;
          const boundary = muscle.boundary_points.map(point => ({
            x: point.x * side.image.width / 1000,
            y: point.y * side.image.height / 1000,
          }));
          const fallback = muscle.grounding_point ? {
            x: muscle.grounding_point.x * side.image.width / 1000,
            y: muscle.grounding_point.y * side.image.height / 1000,
          } : null;
          return <g key={muscle.name} className={`muscle-overlay diagnostic-muscle ${active ? "active" : ""}`}
            onClick={() => onSelect(muscle.name)} tabIndex={0} role="button" aria-label={`Select ${muscle.display_name}`}>
            {layers.template && <path
              d={smoothClosedPath(muscle.template_annotation.pixel_points)}
              className="diagnostic-template"
            ><title>{muscle.display_name}: MediaPipe anatomical template</title></path>}
            {layers.muse && <g className="diagnostic-muse">
              {box && <rect
                x={box.x_min * side.image.width / 1000}
                y={box.y_min * side.image.height / 1000}
                width={(box.x_max - box.x_min) * side.image.width / 1000}
                height={(box.y_max - box.y_min) * side.image.height / 1000}
              />}
              {boundary.length > 1 && <polyline
                points={boundary.map(point => `${point.x},${point.y}`).join(" ")}
              />}
              {boundary.map((point, index) => <circle key={index} cx={point.x} cy={point.y} r="3.5" />)}
              {fallback && <circle className="grounding-centre" cx={fallback.x} cy={fallback.y} r="5" />}
            </g>}
            {layers.final && <path
              d={smoothClosedPath(muscle.annotation.pixel_points)}
              className={`diagnostic-final ${muscle.annotation.shape === "estimated_area" ? "estimated-area" : "surface-region"} ${muscle.location_quality === "covered_surface" ? "covered-surface" : ""}`}
            ><title>{muscle.display_name}: final generated approximation</title></path>}
            {active && layers.final && <>
              <line className="diagnostic-label-line" x1={anchor.x} y1={anchor.y} x2={labelPoint.x} y2={labelPoint.y} />
              <text x={labelPoint.x} y={labelPoint.y}
                textAnchor={labelPoint.x < side.image.width / 2 ? "start" : "end"}>{muscle.display_name}</text>
            </>}
          </g>;
        })}
      </svg>
    </div>
  </article>;
}

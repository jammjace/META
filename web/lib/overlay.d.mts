export type OverlayPoint = { x: number; y: number };
export type MuscleStyle = { fill: string; stroke: string };
export const MUSCLE_STYLES: Readonly<Record<string, MuscleStyle>>;
export function muscleStyle(group: string): MuscleStyle;
export function smoothClosedPath(points: OverlayPoint[]): string;


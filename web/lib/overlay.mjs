export const MUSCLE_STYLES = Object.freeze({
  trapezius: { fill: "#ef765f", stroke: "#8f3528" },
  latissimus: { fill: "#e4c94f", stroke: "#82701d" },
  rhomboids: { fill: "#58bddd", stroke: "#246d85" },
  deltoids: { fill: "#9a7bd5", stroke: "#55407e" },
});

export function muscleStyle(group) {
  return MUSCLE_STYLES[group] ?? { fill: "#b9c2bb", stroke: "#59615c" };
}

/** Closed Catmull-Rom-style curve through landmark-anchored control points. */
export function smoothClosedPath(points) {
  if (!points?.length) return "";
  const midpoint = (a, b) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });
  const start = midpoint(points.at(-1), points[0]);
  const commands = [`M ${start.x} ${start.y}`];
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index];
    const next = points[(index + 1) % points.length];
    const end = midpoint(current, next);
    commands.push(`Q ${current.x} ${current.y} ${end.x} ${end.y}`);
  }
  commands.push("Z");
  return commands.join(" ");
}


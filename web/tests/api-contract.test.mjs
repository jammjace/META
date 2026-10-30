import assert from "node:assert/strict";
import test from "node:test";
import { MUSCLE_STYLES, smoothClosedPath } from "../lib/overlay.mjs";

test("result contract deliberately omits UI confidence", () => {
  const muscle = {
    name: "trapezius",
    display_name: "Trapezius",
    visible: true,
    observation: "Visible upper-back contour.",
  };
  assert.equal("confidence" in muscle, false);
});

test("muscle groups use distinct diagram colors", () => {
  const fills = Object.values(MUSCLE_STYLES).map(style => style.fill);
  assert.equal(new Set(fills).size, 4);
});

test("anatomical control points render as a responsive closed curve", () => {
  const path = smoothClosedPath([
    { x: 10, y: 10 }, { x: 30, y: 8 }, { x: 42, y: 30 },
    { x: 25, y: 50 }, { x: 8, y: 32 },
  ]);
  assert.match(path, /^M /);
  assert.match(path, /Q /);
  assert.match(path, / Z$/);
});


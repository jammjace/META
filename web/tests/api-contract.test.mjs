import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { MUSCLE_STYLES, smoothClosedPath } from "../lib/overlay.mjs";

test("identification contract deliberately omits UI confidence", () => {
  const muscle = {
    name: "trapezius",
    display_name: "Trapezius",
    visible: true,
    observation: "Visible upper-back contour.",
  };
  assert.equal("confidence" in muscle, false);
});

test("seven anatomical groups use distinct diagram colors", () => {
  const fills = Object.values(MUSCLE_STYLES).map(style => style.fill);
  assert.equal(new Set(fills).size, 7);
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

test("diagnostic view exposes independent template, Muse, and final layers", () => {
  const view = readFileSync(new URL("../components/identification-view.tsx", import.meta.url), "utf8");
  const photo = readFileSync(new URL("../components/annotated-photo.tsx", import.meta.url), "utf8");
  assert.match(view, /template: true, muse: true, final: true/);
  assert.match(view, /MediaPipe template/);
  assert.match(view, /Muse raw localization/);
  assert.match(view, /Final outline/);
  assert.match(photo, /grounding_box/);
  assert.match(photo, /boundary_points/);
  assert.match(photo, /template_annotation/);
});


export type Point = { x: number; y: number };

export type MuscleGroup = "chest" | "shoulders" | "arms" | "back" | "core" | "obliques" | "spine";

export type Annotation = {
  shape: "polygon" | "estimated_area";
  normalized_points: Point[];
  pixel_points: { x: number; y: number }[];
  label_anchor: Point;
  label_position: Point;
};

export type GroundingBox = { x_min: number; y_min: number; x_max: number; y_max: number };

export type IdentifiedMuscle = {
  name: string;
  display_name: string;
  group: MuscleGroup;
  side: "left" | "right" | "centre";
  visible: boolean;
  annotation: Annotation;
  template_annotation: Annotation;
  location_quality: "visible_surface" | "covered_surface" | "estimated_deep";
  observation: string;
  grounding_point: { x: number; y: number } | null;
  grounding_box: GroundingBox | null;
  boundary_points: { x: number; y: number }[];
};

export type IdentificationSide = {
  image: { width: number; height: number; url: string };
  view: "front" | "back";
  muscles: IdentifiedMuscle[];
};

export type IdentificationResult = {
  identification_id: string;
  status: "complete";
  front: IdentificationSide;
  back: IdentificationSide;
  warnings: string[];
  model: { provider: string; name: string };
};

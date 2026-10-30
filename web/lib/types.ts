export type Point = { x: number; y: number };

export type MuscleResult = {
  name: string;
  display_name: string;
  group: "trapezius" | "latissimus" | "rhomboids" | "deltoids";
  side: "left" | "right" | "centre";
  visible: boolean;
  annotation: {
    shape: "polygon";
    normalized_points: Point[];
    pixel_points: { x: number; y: number }[];
    label_anchor: Point;
    label_position: Point;
  };
  observation: string;
};

export type AnalysisResult = {
  analysis_id: string;
  status: "complete";
  image: { width: number; height: number; url: string };
  view: "back" | "front" | "uncertain";
  muscles: MuscleResult[];
  warnings: string[];
  model: { provider: string; name: string };
};

export type MuscleProgress = {
  muscle: string;
  status: "visible_progress" | "no_clear_change" | "inconclusive";
  observation: string;
  limitation: string | null;
};

export type ComparisonSide = {
  image: { width: number; height: number; url: string };
  view: "back" | "front" | "uncertain";
  annotations: Omit<MuscleResult, "observation">[];
};

export type ComparisonResult = {
  comparison_id: string;
  status: "complete";
  baseline: ComparisonSide;
  current: ComparisonSide;
  overall_summary: string;
  muscle_progress: MuscleProgress[];
  comparison_warnings: string[];
  model: { provider: string; name: string };
};


from __future__ import annotations

from models import Annotation, MuscleRegion, PixelPoint, Point
from services.pose_detector import PoseDetection


def _mix(a: Point, b: Point, t: float) -> Point:
    return Point(x=a.x + (b.x - a.x) * t, y=a.y + (b.y - a.y) * t)


def _point(x: float, y: float) -> Point:
    return Point(x=min(max(x, 0), 1), y=min(max(y, 0), 1))


def _region(
    name: str,
    display: str,
    group: str,
    side: str,
    points: list[Point],
    label_anchor: Point,
    label_position: Point,
    width: int,
    height: int,
) -> MuscleRegion:
    pixels = [
        PixelPoint(x=min(round(p.x * width), width - 1), y=min(round(p.y * height), height - 1))
        for p in points
    ]
    return MuscleRegion(
        name=name,
        display_name=display,
        group=group,
        side=side,
        annotation=Annotation(
            normalized_points=points,
            pixel_points=pixels,
            label_anchor=label_anchor,
            label_position=label_position,
        ),
    )


def build_back_annotations(
    pose: PoseDetection, width: int, height: int
) -> list[MuscleRegion]:
    """Approximate back regions anchored to MediaPipe shoulders, elbows, and hips."""
    l_sh, r_sh = pose.landmarks[11], pose.landmarks[12]
    l_el, r_el = pose.landmarks[13], pose.landmarks[14]
    l_hip, r_hip = pose.landmarks[23], pose.landmarks[24]
    shoulder_width = max(abs(r_sh.x - l_sh.x), 0.12)
    torso_top = (l_sh.y + r_sh.y) / 2
    torso_bottom = (l_hip.y + r_hip.y) / 2
    torso_height = max(torso_bottom - torso_top, 0.18)
    centre_x = (l_sh.x + r_sh.x) / 2
    neck = _point(centre_x, torso_top - torso_height * 0.13)
    upper_centre = _point(centre_x, torso_top + torso_height * 0.22)
    mid_centre = _point(centre_x, torso_top + torso_height * 0.46)
    lower_centre = _point(centre_x, torso_top + torso_height * 0.76)
    left_inner = centre_x - shoulder_width * 0.075
    right_inner = centre_x + shoulder_width * 0.075

    regions = [
        _region("trapezius", "Trapezius", "trapezius", "centre", [
            neck,
            _mix(neck, l_sh, 0.34),
            _mix(neck, l_sh, 0.72),
            _point(centre_x - shoulder_width * 0.27, upper_centre.y),
            _point(centre_x - shoulder_width * 0.15, mid_centre.y),
            _point(centre_x, torso_top + torso_height * 0.62),
            _point(centre_x + shoulder_width * 0.15, mid_centre.y),
            _point(centre_x + shoulder_width * 0.27, upper_centre.y),
            _mix(neck, r_sh, 0.72),
            _mix(neck, r_sh, 0.34),
        ], upper_centre, _point(0.08, torso_top + torso_height * 0.08), width, height),
        _region("left_rhomboid", "Left rhomboids", "rhomboids", "left", [
            _point(left_inner, torso_top + torso_height * 0.22),
            _point(centre_x - shoulder_width * 0.23, torso_top + torso_height * 0.30),
            _point(centre_x - shoulder_width * 0.27, torso_top + torso_height * 0.43),
            _point(centre_x - shoulder_width * 0.15, torso_top + torso_height * 0.55),
            _point(left_inner, torso_top + torso_height * 0.48),
        ], _point(centre_x - shoulder_width * 0.18, torso_top + torso_height * 0.38),
            _point(0.08, torso_top + torso_height * 0.36), width, height),
        _region("right_rhomboid", "Right rhomboids", "rhomboids", "right", [
            _point(right_inner, torso_top + torso_height * 0.22),
            _point(right_inner, torso_top + torso_height * 0.48),
            _point(centre_x + shoulder_width * 0.15, torso_top + torso_height * 0.55),
            _point(centre_x + shoulder_width * 0.27, torso_top + torso_height * 0.43),
            _point(centre_x + shoulder_width * 0.23, torso_top + torso_height * 0.30),
        ], _point(centre_x + shoulder_width * 0.18, torso_top + torso_height * 0.38),
            _point(0.92, torso_top + torso_height * 0.36), width, height),
        _region("left_latissimus_dorsi", "Left latissimus dorsi", "latissimus", "left", [
            _point(centre_x - shoulder_width * 0.29, torso_top + torso_height * 0.36),
            _mix(l_sh, l_hip, 0.38),
            _mix(l_sh, l_hip, 0.58),
            _point(l_hip.x - shoulder_width * 0.11, l_hip.y - torso_height * 0.06),
            _point(l_hip.x + shoulder_width * 0.03, l_hip.y - torso_height * 0.02),
            _point(centre_x - shoulder_width * 0.08, lower_centre.y),
            _point(centre_x - shoulder_width * 0.09, mid_centre.y),
        ], _point(centre_x - shoulder_width * 0.25, torso_top + torso_height * 0.60),
            _point(0.08, torso_top + torso_height * 0.67), width, height),
        _region("right_latissimus_dorsi", "Right latissimus dorsi", "latissimus", "right", [
            _point(centre_x + shoulder_width * 0.29, torso_top + torso_height * 0.36),
            _point(centre_x + shoulder_width * 0.09, mid_centre.y),
            _point(centre_x + shoulder_width * 0.08, lower_centre.y),
            _point(r_hip.x - shoulder_width * 0.03, r_hip.y - torso_height * 0.02),
            _point(r_hip.x + shoulder_width * 0.11, r_hip.y - torso_height * 0.06),
            _mix(r_sh, r_hip, 0.58),
            _mix(r_sh, r_hip, 0.38),
        ], _point(centre_x + shoulder_width * 0.25, torso_top + torso_height * 0.60),
            _point(0.92, torso_top + torso_height * 0.67), width, height),
    ]
    for side, shoulder, elbow, sign in (
        ("left", l_sh, l_el, -1), ("right", r_sh, r_el, 1)
    ):
        arm = _mix(shoulder, elbow, 0.2)
        radius_x = shoulder_width * 0.105
        radius_y = torso_height * 0.075
        outer_x = shoulder.x + sign * radius_x
        regions.append(_region(
            f"{side}_posterior_deltoid", f"{side.title()} posterior deltoid", "deltoids", side,
            [
                _point(shoulder.x - sign * radius_x * 0.50, shoulder.y - radius_y * 0.20),
                _point(shoulder.x, shoulder.y - radius_y * 0.70),
                _point(outer_x, shoulder.y - radius_y * 0.15),
                _point(arm.x + sign * radius_x * 0.75, arm.y + radius_y * 0.20),
                _point(arm.x, arm.y + radius_y * 0.75),
                _point(shoulder.x - sign * radius_x * 0.45, shoulder.y + radius_y * 0.55),
            ], shoulder,
            _point(0.08 if shoulder.x < centre_x else 0.92, shoulder.y - radius_y * 0.75),
            width, height
        ))
    return regions


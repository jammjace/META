from __future__ import annotations

import math

from models import Annotation, MuscleRegion, PixelPoint, Point
from services.pose_detector import PoseDetection


def _mix(a: Point, b: Point, t: float) -> Point:
    return Point(x=a.x + (b.x - a.x) * t, y=a.y + (b.y - a.y) * t)


def _point(x: float, y: float) -> Point:
    return Point(x=min(max(x, 0), 1), y=min(max(y, 0), 1))


def _region(name: str, display: str, group: str, side: str, points: list[Point],
            label_anchor: Point, label_position: Point, width: int, height: int) -> MuscleRegion:
    pixels = [PixelPoint(x=min(round(p.x * width), width - 1), y=min(round(p.y * height), height - 1)) for p in points]
    return MuscleRegion(name=name, display_name=display, group=group, side=side,
        annotation=Annotation(normalized_points=points, pixel_points=pixels,
                              label_anchor=label_anchor, label_position=label_position))


def _arm_band(shoulder: Point, elbow: Point, start: float, end: float, width: float) -> list[Point]:
    """Tapered region aligned to the actual shoulder/elbow axis."""
    top, bottom = _mix(shoulder, elbow, start), _mix(shoulder, elbow, end)
    dx, dy = elbow.x - shoulder.x, elbow.y - shoulder.y
    length = max(math.hypot(dx, dy), .001)
    px, py = -dy / length, dx / length
    middle = _mix(top, bottom, .5)
    return [
        _point(top.x + px * width * .72, top.y + py * width * .72),
        _point(top.x - px * width * .72, top.y - py * width * .72),
        _point(middle.x - px * width, middle.y - py * width),
        _point(bottom.x - px * width * .58, bottom.y - py * width * .58),
        _point(bottom.x + px * width * .58, bottom.y + py * width * .58),
        _point(middle.x + px * width, middle.y + py * width),
    ]


def _torso_metrics(pose: PoseDetection):
    l_sh, r_sh = pose.landmarks[11], pose.landmarks[12]
    l_hip, r_hip = pose.landmarks[23], pose.landmarks[24]
    sw = max(abs(r_sh.x - l_sh.x), .12)
    top, bottom = (l_sh.y + r_sh.y) / 2, (l_hip.y + r_hip.y) / 2
    th = max(bottom - top, .18)
    centre, hip_centre = (l_sh.x + r_sh.x) / 2, (l_hip.x + r_hip.x) / 2
    return l_sh, r_sh, l_hip, r_hip, sw, top, bottom, th, centre, hip_centre


def build_front_annotations(pose: PoseDetection, width: int, height: int) -> list[MuscleRegion]:
    """Pose-conditioned front templates; approximate anatomy, never segmentation."""
    l_sh, r_sh, l_hip, r_hip, sw, top, bottom, th, centre, hip_centre = _torso_metrics(pose)
    elbows = {"left": pose.landmarks.get(13), "right": pose.landmarks.get(14)}
    regions: list[MuscleRegion] = []
    for side, shoulder, hip in (("left", l_sh, l_hip), ("right", r_sh, r_hip)):
        elbow = elbows[side]
        sign = 1 if shoulder.x > centre else -1
        sternum = centre + sign * sw * .018
        lower_y = top + th * .285
        chest = [
            _point(sternum, shoulder.y + th * .015),
            _point(centre + sign * sw * .15, top - th * .015),
            _point(centre + sign * sw * .29, shoulder.y + th * .025),
            _point(centre + sign * sw * .43, top + th * .105),
            _point(centre + sign * sw * .42, top + th * .215),
            _point(centre + sign * sw * .32, lower_y),
            _point(centre + sign * sw * .13, lower_y + th * .012),
            _point(sternum, top + th * .245),
        ]
        regions.append(_region(f"{side}_pectoralis_major", f"{side.title()} pectoralis major", "chest", side,
            chest, _point(centre + sign * sw * .21, top + th * .15),
            _point(.94 if sign > 0 else .06, top + th * .15), width, height))

        oblique = [
            _point(centre + sign * sw * .29, top + th * .31),
            _point(centre + sign * sw * .36, top + th * .38),
            _point(centre + sign * sw * .34, top + th * .57),
            _point(hip.x + sign * sw * .055, bottom - th * .035),
            _point(hip_centre + sign * sw * .19, bottom + th * .015),
            _point(centre + sign * sw * .14, top + th * .72),
            _point(centre + sign * sw * .15, top + th * .45),
        ]
        regions.append(_region(f"{side}_external_oblique", f"{side.title()} external oblique / serratus", "obliques", side,
            oblique, _point(centre + sign * sw * .25, top + th * .62),
            _point(.94 if sign > 0 else .06, top + th * .66), width, height))

        if elbow is None:
            continue
        upper_arm = _mix(shoulder, elbow, .24)
        inward = -sign
        anterior = [
            _point(shoulder.x + inward * sw * .12, shoulder.y - th * .012),
            _point(shoulder.x, shoulder.y - th * .10),
            _point(shoulder.x + sign * sw * .09, shoulder.y - th * .045),
            _point(upper_arm.x + sign * sw * .045, upper_arm.y + th * .02),
            _point(upper_arm.x + inward * sw * .04, upper_arm.y + th * .07),
            _point(shoulder.x + inward * sw * .13, shoulder.y + th * .07),
        ]
        lateral = [
            _point(shoulder.x, shoulder.y - th * .10),
            _point(shoulder.x + sign * sw * .15, shoulder.y - th * .02),
            _point(upper_arm.x + sign * sw * .11, upper_arm.y + th * .035),
            _point(upper_arm.x + sign * sw * .025, upper_arm.y + th * .10),
            _point(upper_arm.x + inward * sw * .04, upper_arm.y + th * .07),
            _point(shoulder.x + sign * sw * .09, shoulder.y - th * .045),
        ]
        regions.extend([
            _region(f"{side}_anterior_deltoid", f"{side.title()} anterior deltoid", "shoulders", side,
                anterior, _mix(shoulder, upper_arm, .35),
                _point(.94 if sign > 0 else .06, shoulder.y - th * .10), width, height),
            _region(f"{side}_lateral_deltoid", f"{side.title()} lateral deltoid", "shoulders", side,
                lateral, _mix(shoulder, upper_arm, .58),
                _point(.94 if sign > 0 else .06, shoulder.y + th * .02), width, height),
        ])
        biceps = _arm_band(shoulder, elbow, .24, .80, sw * .085)
        regions.append(_region(f"{side}_biceps_brachii", f"{side.title()} biceps brachii", "arms", side,
            biceps, _mix(shoulder, elbow, .52),
            _point(.95 if sign > 0 else .05, _mix(shoulder, elbow, .52).y), width, height))

    rectus = [
        _point(centre - sw * .17, top + th * .30), _point(centre + sw * .17, top + th * .30),
        _point(centre + sw * .19, top + th * .48), _point(hip_centre + sw * .16, top + th * .70),
        _point(hip_centre + sw * .12, bottom + th * .018), _point(hip_centre - sw * .12, bottom + th * .018),
        _point(hip_centre - sw * .16, top + th * .70), _point(centre - sw * .19, top + th * .48),
    ]
    regions.append(_region("rectus_abdominis", "Rectus abdominis", "core", "centre", rectus,
        _point((centre + hip_centre) / 2, top + th * .61),
        _point(.5, min(.96, bottom + th * .11)), width, height))
    return regions


def build_back_annotations(pose: PoseDetection, width: int, height: int) -> list[MuscleRegion]:
    """Pose-conditioned posterior templates with deep anatomy kept compact."""
    l_sh, r_sh, l_hip, r_hip, sw, top, bottom, th, centre, hip_centre = _torso_metrics(pose)
    elbows = {"left": pose.landmarks.get(13), "right": pose.landmarks.get(14)}
    neck = _point(centre, top - th * .17)
    regions: list[MuscleRegion] = []
    trap = [neck, _mix(neck, l_sh, .38), _mix(neck, l_sh, .78),
        _point(centre - sw * .30, top + th * .12), _point(centre - sw * .18, top + th * .25),
        _point(centre - sw * .07, top + th * .42), _point(centre, top + th * .50),
        _point(centre + sw * .07, top + th * .42), _point(centre + sw * .18, top + th * .25),
        _point(centre + sw * .30, top + th * .12), _mix(neck, r_sh, .78), _mix(neck, r_sh, .38)]
    regions.append(_region("trapezius", "Trapezius", "back", "centre", trap,
        _point(centre, top + th * .20), _point(.08, top - th * .02), width, height))

    for side, shoulder, elbow, hip in (("left", l_sh, elbows["left"], l_hip), ("right", r_sh, elbows["right"], r_hip)):
        sign = -1 if shoulder.x < centre else 1
        rhomboid = [_point(centre + sign * sw * .055, top + th * .23),
            _point(centre + sign * sw * .20, top + th * .29), _point(centre + sign * sw * .22, top + th * .43),
            _point(centre + sign * sw * .09, top + th * .52), _point(centre + sign * sw * .045, top + th * .42)]
        regions.append(_region(f"{side}_rhomboid", f"{side.title()} rhomboids", "back", side,
            rhomboid, _point(centre + sign * sw * .13, top + th * .37),
            _point(.08 if sign < 0 else .92, top + th * .34), width, height))

        lat = [_point(centre + sign * sw * .33, top + th * .31), _point(centre + sign * sw * .47, top + th * .37),
            _point(centre + sign * sw * .52, top + th * .54), _point(hip.x + sign * sw * .08, bottom - th * .03),
            _point(hip_centre + sign * sw * .12, bottom + th * .015), _point(centre + sign * sw * .09, top + th * .76),
            _point(centre + sign * sw * .10, top + th * .51)]
        regions.append(_region(f"{side}_latissimus_dorsi", f"{side.title()} latissimus dorsi", "back", side,
            lat, _point(centre + sign * sw * .27, top + th * .62),
            _point(.08 if sign < 0 else .92, top + th * .67), width, height))

        if elbow is None:
            continue
        upper_arm = _mix(shoulder, elbow, .24)
        posterior = [_point(shoulder.x - sign * sw * .11, shoulder.y - th * .025),
            _point(shoulder.x, shoulder.y - th * .09), _point(shoulder.x + sign * sw * .15, shoulder.y - th * .01),
            _point(upper_arm.x + sign * sw * .11, upper_arm.y + th * .04),
            _point(upper_arm.x, upper_arm.y + th * .10), _point(upper_arm.x - sign * sw * .06, upper_arm.y + th * .035)]
        regions.append(_region(f"{side}_posterior_deltoid", f"{side.title()} posterior deltoid", "shoulders", side,
            posterior, _mix(shoulder, upper_arm, .5),
            _point(.07 if sign < 0 else .93, shoulder.y - th * .08), width, height))
        triceps = _arm_band(shoulder, elbow, .26, .82, sw * .08)
        regions.append(_region(f"{side}_triceps_brachii", f"{side.title()} triceps brachii", "arms", side,
            triceps, _mix(shoulder, elbow, .54),
            _point(.05 if sign < 0 else .95, _mix(shoulder, elbow, .54).y), width, height))

    erector = [_point(centre - sw * .055, top + th * .50), _point(centre + sw * .055, top + th * .50),
               _point(hip_centre + sw * .075, bottom), _point(hip_centre - sw * .075, bottom)]
    regions.append(_region("erector_spinae", "Erector spinae", "spine", "centre", erector,
        _point((centre + hip_centre) / 2, top + th * .73),
        _point(.5, min(.97, bottom + th * .08)), width, height))
    return regions

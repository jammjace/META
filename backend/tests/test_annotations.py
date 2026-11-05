import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from models import GroundingPoint, Point
from services.identification_pipeline import _ground_region
from services.annotation_builder import build_back_annotations, build_front_annotations
from services.pose_detector import PoseDetection


def test_builds_expected_back_muscles_with_bounded_coordinates():
    points = {
        11: Point(x=.3, y=.25), 12: Point(x=.7, y=.25),
        13: Point(x=.2, y=.5), 14: Point(x=.8, y=.5),
        23: Point(x=.38, y=.72), 24: Point(x=.62, y=.72),
    }
    regions = build_back_annotations(PoseDetection(points, {i: 1 for i in points}), 800, 1000)
    names = {region.name for region in regions}
    assert names == {
        "trapezius", "left_rhomboid", "right_rhomboid",
        "left_latissimus_dorsi", "right_latissimus_dorsi",
        "left_posterior_deltoid", "right_posterior_deltoid",
        "left_triceps_brachii", "right_triceps_brachii",
        "erector_spinae",
    }
    assert all(0 <= p.x <= 1 and 0 <= p.y <= 1 for r in regions for p in r.annotation.normalized_points)
    assert all(0 <= p.x < 800 and 0 <= p.y < 1000 for r in regions for p in r.annotation.pixel_points)
    assert all(len(region.annotation.normalized_points) >= 4 for region in regions)
    assert {region.group for region in regions} == {"back", "shoulders", "arms", "spine"}
    assert all(0 <= region.annotation.label_anchor.x <= 1 for region in regions)
    assert all(0 <= region.annotation.label_position.y <= 1 for region in regions)


def test_regions_are_bilateral_and_do_not_cross_the_spine():
    points = {
        11: Point(x=.3, y=.25), 12: Point(x=.7, y=.25),
        13: Point(x=.2, y=.5), 14: Point(x=.8, y=.5),
        23: Point(x=.38, y=.72), 24: Point(x=.62, y=.72),
    }
    regions = build_back_annotations(PoseDetection(points, {i: 1 for i in points}), 800, 1000)
    for region in regions:
        xs = [point.x for point in region.annotation.normalized_points]
        if region.side == "left":
            assert max(xs) <= .5
        elif region.side == "right":
            assert min(xs) >= .5


def test_front_regions_cover_chest_shoulders_arms_and_core():
    points = {
        11: Point(x=.7, y=.25), 12: Point(x=.3, y=.25),
        13: Point(x=.8, y=.5), 14: Point(x=.2, y=.5),
        23: Point(x=.62, y=.72), 24: Point(x=.38, y=.72),
    }
    regions = build_front_annotations(PoseDetection(points, {i: 1 for i in points}), 800, 1000)
    assert {region.group for region in regions} == {"chest", "shoulders", "arms", "core", "obliques"}
    assert {region.name for region in regions} == {
        "left_pectoralis_major", "right_pectoralis_major",
        "left_anterior_deltoid", "right_anterior_deltoid",
        "left_lateral_deltoid", "right_lateral_deltoid",
        "left_biceps_brachii", "right_biceps_brachii",
        "left_external_oblique", "right_external_oblique", "rectus_abdominis",
    }


def test_manual_reference_points_pull_regions_without_crossing_anatomical_side():
    references = json.loads(
        (Path(__file__).parent / "fixtures" / "anatomical_reference_points.json").read_text()
    )
    points = {
        11: Point(x=.70, y=.25), 12: Point(x=.30, y=.25),
        13: Point(x=.82, y=.52), 14: Point(x=.18, y=.52),
        23: Point(x=.62, y=.72), 24: Point(x=.38, y=.72),
    }
    pose = PoseDetection(points, {index: 1 for index in points})
    regions = {region.name: region for region in build_front_annotations(pose, 800, 1000)}
    region = regions["left_pectoralis_major"]
    before = tuple(sum(getattr(p, axis) for p in region.annotation.normalized_points) / len(region.annotation.normalized_points) for axis in ("x", "y"))
    target = references["front"][region.name]
    grounded = _ground_region(
        region, GroundingPoint(x=round(target[0] * 1000), y=round(target[1] * 1000)),
        pose, 800, 1000, False,
    )
    assert grounded is not None
    after = tuple(sum(getattr(p, axis) for p in grounded.annotation.normalized_points) / len(grounded.annotation.normalized_points) for axis in ("x", "y"))
    before_distance = sum((before[i] - target[i]) ** 2 for i in (0, 1)) ** .5
    after_distance = sum((after[i] - target[i]) ** 2 for i in (0, 1)) ** .5
    assert after_distance < before_distance
    assert min(point.x for point in grounded.annotation.normalized_points) > .5


def test_deep_rhomboid_is_compact_estimated_area_at_reviewed_anchor():
    references = json.loads(
        (Path(__file__).parent / "fixtures" / "anatomical_reference_points.json").read_text()
    )
    points = {
        11: Point(x=.30, y=.25), 12: Point(x=.70, y=.25),
        13: Point(x=.18, y=.52), 14: Point(x=.82, y=.52),
        23: Point(x=.38, y=.72), 24: Point(x=.62, y=.72),
    }
    pose = PoseDetection(points, {index: 1 for index in points})
    region = next(r for r in build_back_annotations(pose, 800, 1000) if r.name == "left_rhomboid")
    target = references["back"][region.name]
    grounded = _ground_region(
        region, GroundingPoint(x=round(target[0] * 1000), y=round(target[1] * 1000)),
        pose, 800, 1000, True,
    )
    assert grounded is not None
    assert grounded.annotation.shape == "estimated_area"
    xs = [point.x for point in grounded.annotation.normalized_points]
    ys = [point.y for point in grounded.annotation.normalized_points]
    assert max(xs) - min(xs) <= .12
    assert max(ys) - min(ys) <= .16


def _mask(region, size=500):
    image = Image.new("1", (size, size), 0)
    ImageDraw.Draw(image).polygon(
        [(round(point.x * size), round(point.y * size)) for point in region.annotation.normalized_points],
        fill=1,
    )
    return image


def _overlap_ratio(first, second):
    a, b = _mask(first), _mask(second)
    pa, pb = list(a.getdata()), list(b.getdata())
    intersection = sum(bool(x and y) for x, y in zip(pa, pb))
    smaller = min(sum(pa), sum(pb))
    return intersection / smaller if smaller else 0


def test_stage2_regions_stay_in_pose_envelopes_and_reduce_unrelated_overlap():
    front_points = {
        11: Point(x=.70, y=.25), 12: Point(x=.30, y=.25),
        13: Point(x=.82, y=.52), 14: Point(x=.18, y=.52),
        23: Point(x=.62, y=.72), 24: Point(x=.38, y=.72),
    }
    pose = PoseDetection(front_points, {index: 1 for index in front_points})
    regions = {region.name: region for region in build_front_annotations(pose, 800, 1000)}
    torso_names = [name for name in regions if any(token in name for token in ("pectoralis", "oblique", "rectus"))]
    for name in torso_names:
        for point in regions[name].annotation.normalized_points:
            assert .20 <= point.x <= .80
            assert .20 <= point.y <= .75
    assert _overlap_ratio(regions["left_pectoralis_major"], regions["rectus_abdominis"]) < .08
    assert _overlap_ratio(regions["left_pectoralis_major"], regions["left_biceps_brachii"]) < .12


def test_stage2_centroids_are_close_to_independently_reviewed_reference_anchors():
    references = json.loads(
        (Path(__file__).parent / "fixtures" / "anatomical_reference_points.json").read_text()
    )
    front_points = {
        11: Point(x=.70, y=.25), 12: Point(x=.30, y=.25),
        13: Point(x=.82, y=.52), 14: Point(x=.18, y=.52),
        23: Point(x=.62, y=.72), 24: Point(x=.38, y=.72),
    }
    back_points = {
        11: Point(x=.30, y=.25), 12: Point(x=.70, y=.25),
        13: Point(x=.18, y=.52), 14: Point(x=.82, y=.52),
        23: Point(x=.38, y=.72), 24: Point(x=.62, y=.72),
    }
    for view, regions in (
        ("front", build_front_annotations(PoseDetection(front_points, {i: 1 for i in front_points}), 800, 1000)),
        ("back", build_back_annotations(PoseDetection(back_points, {i: 1 for i in back_points}), 800, 1000)),
    ):
        for region in regions:
            target = references[view][region.name]
            points = region.annotation.normalized_points
            centroid = (sum(p.x for p in points) / len(points), sum(p.y for p in points) / len(points))
            distance = ((centroid[0] - target[0]) ** 2 + (centroid[1] - target[1]) ** 2) ** .5
            assert distance < .14, f"{region.name} centroid drifted {distance:.3f} from reviewed anchor"


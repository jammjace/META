from models import Point
from services.annotation_builder import build_back_annotations
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
    }
    assert all(0 <= p.x <= 1 and 0 <= p.y <= 1 for r in regions for p in r.annotation.normalized_points)
    assert all(0 <= p.x < 800 and 0 <= p.y < 1000 for r in regions for p in r.annotation.pixel_points)
    assert all(len(region.annotation.normalized_points) >= 5 for region in regions)
    assert {region.group for region in regions} == {
        "trapezius", "latissimus", "rhomboids", "deltoids"
    }
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


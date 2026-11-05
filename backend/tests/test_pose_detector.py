from types import SimpleNamespace

from services.image_preprocessor import ImageTransform
from services.pose_detector import PoseDetection, _map_pose_landmarks
from models import Point


def landmark(x, y, visibility=1.0):
    return SimpleNamespace(x=x, y=y, z=0.0, visibility=visibility)


def test_letterbox_projection_rejects_padding_landmark_instead_of_clamping():
    transform = ImageTransform(
        source_width=800, source_height=1000,
        inference_width=1000, inference_height=1000,
        scaled_width=800, scaled_height=1000, offset_x=100, offset_y=0,
    )
    points, visibility, depth, invalid = _map_pose_landmarks(
        [landmark(.05, .5), landmark(.5, .5)], transform
    )
    assert 0 in invalid and 0 not in points
    assert points[1] == Point(x=.5, y=.5)
    assert visibility[0] == 1 and depth[0] == 0


def test_expected_view_accepts_mirror_and_marks_it_explicitly():
    normal_front = PoseDetection(
        {11: Point(x=.7, y=.3), 12: Point(x=.3, y=.3)}, {11: 1, 12: 1}
    )
    mirrored_front = PoseDetection(
        {11: Point(x=.3, y=.3), 12: Point(x=.7, y=.3)}, {11: 1, 12: 1}
    )
    assert normal_front.assess_view("front") == ("front", False)
    assert mirrored_front.assess_view("front") == ("front", True)

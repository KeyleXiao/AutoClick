import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from KeyleFinderModule import KeyleFinderModule


def test_locate_demo_images():
    finder = KeyleFinderModule('demo/layer.png')
    result = finder.locate('demo/middle.png')
    assert result["status"] == 0
    tl = result["top_left"]
    br = result["bottom_right"]
    width = br[0] - tl[0]
    height = br[1] - tl[1]
    assert 300 <= width <= 330
    assert 320 <= height <= 340

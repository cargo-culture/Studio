from studio_runner.github import slugify

def test_slugify():
    assert slugify("Polygon Collision: Mobile + Edge Cases") == "polygon-collision-mobile-edge-cases"

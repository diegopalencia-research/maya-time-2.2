from astronomy_layer import calculate_aspects


def test_calculate_aspects_detects_major_aspect_and_symbolic_reading():
    positions = [
        {"body": "Mercury", "longitude": 10.0},
        {"body": "Saturn", "longitude": 101.5},
        {"body": "Venus", "longitude": 191.0},
    ]

    aspects = calculate_aspects(positions, orb_limit=6.0)

    assert [(row["body_a"], row["body_b"], row["aspect"]) for row in aspects] == [
        ("Saturn", "Venus", "Square"),
        ("Mercury", "Venus", "Opposition"),
        ("Mercury", "Saturn", "Square"),
    ]
    assert aspects[0]["orb"] == 0.5
    assert "traditional" in aspects[0]["interpretation"]


def test_calculate_aspects_wraps_around_zero_degrees():
    positions = [
        {"body": "Sun", "longitude": 358.0},
        {"body": "Moon", "longitude": 2.0},
    ]

    aspects = calculate_aspects(positions, orb_limit=6.0)

    assert len(aspects) == 1
    assert aspects[0]["aspect"] == "Conjunction"
    assert aspects[0]["angle"] == 4.0
    assert aspects[0]["orb"] == 4.0


def test_calculate_aspects_excludes_pairs_outside_orb():
    positions = [
        {"body": "Sun", "longitude": 0.0},
        {"body": "Mars", "longitude": 103.0},
    ]
    assert calculate_aspects(positions, orb_limit=6.0) == []

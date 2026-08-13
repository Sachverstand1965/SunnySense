from custom_components.is_sunny.model import (
    SunnyModel, active_facade, incidence_factor, learning_allowed,
)


def test_facade_selection_and_wraparound():
    assert active_facade(10)["name"] == "northeast"
    assert active_facade(101.88)["name"] == "northeast"
    assert active_facade(200)["name"] == "southwest"
    assert active_facade(300)["name"] == "northwest"
    assert active_facade(115) is None


def test_overlap_uses_nearest_facade():
    assert active_facade(250)["name"] == "southwest"
    assert active_facade(260)["name"] == "northwest"


def test_roof_window_incidence_geometry():
    facing = incidence_factor(25, 48, 25, 42)
    assert facing > 0.99
    assert incidence_factor(205, 10, 25, 42) < 0


def test_learning_and_roundtrip():
    model = SunnyModel()
    for value in (5000, 5200, 5100, 5300, 5250, 5400, 5350, 5450):
        model.learn("southwest", 205, 40, value)
    estimate = model.estimate("southwest", 205, 40)
    assert estimate.expected is not None
    assert 5000 < estimate.expected < 5450
    assert estimate.samples == 8
    restored = SunnyModel(model.as_dict()).estimate("southwest", 205, 40)
    assert restored.expected == estimate.expected


def test_adaptive_hysteresis_remains_safe():
    model = SunnyModel()
    for _ in range(100):
        model.adapt_thresholds("southwest", 0.95, True)
        model.adapt_thresholds("southwest", 0.50, False)
    thresholds = model.thresholds["southwest"]
    assert 0.72 <= thresholds["on"] <= 0.92
    assert thresholds["off"] <= thresholds["on"] - 0.10


def test_learning_gate():
    assert learning_allowed(elevation=30, pv=4000, lux=50000, cloud=10, temperature=20)
    assert not learning_allowed(elevation=5, pv=4000, lux=50000, cloud=10, temperature=20)
    assert not learning_allowed(elevation=30, pv=4000, lux=1000, cloud=90, temperature=20)

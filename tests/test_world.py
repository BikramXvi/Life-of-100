from life100.simulation.world import WorldConfig, generate_world


def test_same_seed_produces_identical_world():
    config = WorldConfig(seed=847291, width=20, height=20)
    world_a = generate_world(config)
    world_b = generate_world(config)
    assert world_a == world_b


def test_different_seed_can_produce_different_world():
    world_a = generate_world(WorldConfig(seed=1, width=20, height=20))
    world_b = generate_world(WorldConfig(seed=2, width=20, height=20))
    assert world_a != world_b


def test_world_has_civic_infrastructure():
    world = generate_world(WorldConfig(seed=847291))
    kinds = {b.kind for b in world.buildings}
    assert {"home", "school", "hospital", "bank", "government", "shop", "factory"} <= kinds


def test_invalid_config_rejected():
    import pytest

    with pytest.raises(ValueError):
        WorldConfig(seed=1, width=0, height=10)

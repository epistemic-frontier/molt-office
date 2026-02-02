from molt_office.world import World


def test_object_history_records_versions():
    world = World()
    world.object_create("ec", "o1", "Title", "Sum", content="v1")
    world.object_append("ec", "o1", " v2")

    event, _ = world.object_history("ec", "o1")
    history = event.data["history"]
    assert history[-1]["version"] == 2
    assert "v2" in history[-1]["content"]

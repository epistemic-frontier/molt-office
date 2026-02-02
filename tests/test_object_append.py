from molt_office.world import World


def test_object_append_increments_version():
    world = World()
    world.object_create("ec", "o1", "Title", "Sum", content="Hello")

    event, _ = world.object_append("ec", "o1", " World")
    assert event.ok is True

    read_event, _ = world.object_read("ec", "o1")
    obj = read_event.data["object"]
    assert obj["content"] == "Hello World"
    assert obj["version"] == 2

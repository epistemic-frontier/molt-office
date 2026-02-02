from molt_office.world import World


def test_object_create_and_read():
    world = World()
    event, _ = world.object_create("ec", "obj-1", "Title", "Summary", content="Hi")
    assert event.ok is True

    read_event, _ = world.object_read("ec", "obj-1")
    assert read_event.ok is True
    assert read_event.data["object"]["title"] == "Title"


def test_object_write_requires_holder():
    world = World()
    world.object_create("ec", "obj-2", "Title", "Summary", content="Hi")

    event, _ = world.object_write("vk", "obj-2", "Nope")
    assert event.ok is False
    assert event.err["code"] == "E_FORBIDDEN"


def test_object_tags():
    world = World()
    world.object_create("ec", "obj-3", "Title", "Summary")

    event, _ = world.object_tags("ec", "obj-3", ["cat:logic", "desc:lemma"])
    assert event.ok is True

    read_event, _ = world.object_read("ec", "obj-3")
    assert "cat:logic" in read_event.data["object"]["tags"]

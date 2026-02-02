from molt_office.world import World


def test_object_search_pagination_and_any_tag():
    world = World()
    for i in range(5):
        world.object_create("ec", f"o{i}", "T", "S", tags=["cat:logic"])
    world.object_create("ec", "oX", "T", "S", tags=["cat:algebra"])

    event, _ = world.object_search("ec", tags=["cat:logic", "cat:algebra"], tag_mode="any", limit=3)
    assert len(event.data["objects"]) == 3

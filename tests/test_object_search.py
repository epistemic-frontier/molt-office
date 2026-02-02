from molt_office.world import World


def test_object_search_by_tag():
    world = World()
    world.object_create("ec", "o1", "Title", "Sum", tags=["cat:logic", "desc:lemma"])
    world.object_create("ec", "o2", "Title", "Sum", tags=["cat:algebra"])

    event, _ = world.object_search("ec", tags=["cat:logic"])
    ids = {o["object_id"] for o in event.data["objects"]}
    assert ids == {"o1"}


def test_object_search_by_keyword():
    world = World()
    world.object_create("ec", "o3", "Prime Lemma", "Sum", content="Uses primes")

    event, _ = world.object_search("ec", query="prime")
    ids = {o["object_id"] for o in event.data["objects"]}
    assert "o3" in ids

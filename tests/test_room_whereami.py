from molt_office.world import World


def test_whereami_none_when_not_in_room():
    world = World()
    event, _ = world.room_whereami("ec")

    assert event.ok is True
    assert event.data["room_id"] is None


def test_whereami_after_enter():
    world = World()
    event, _ = world.room_enter("ec", "lobby")
    assert event.ok is True

    where_event, _ = world.room_whereami("ec")
    assert where_event.data["room_id"] == "lobby"

from molt_office.world import World


def test_knock_public_room_conflict():
    world = World()
    event, _ = world.room_knock("ec", "lobby")

    assert event.ok is False
    assert event.err["code"] == "E_CONFLICT"
